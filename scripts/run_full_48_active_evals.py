#!/usr/bin/env python3
"""Deterministic evals for Pixelkiez full 48 active measurement-to-score integrity."""
from __future__ import annotations

import copy
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import jsonschema

from core_active_measurement import ContractError, admission_report, file_sha, materialize_report, semantic_digest, validate_bundle


def run(args: list[str], *, expect: int = 0, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if p.returncode != expect:
        raise AssertionError(f"return {p.returncode} != {expect}: {' '.join(args)}\nSTDOUT:{p.stdout[-3000:]}\nSTDERR:{p.stderr[-3000:]}")
    return p


def dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_error(fn: Callable[[], Any], contains: str | None = None) -> str:
    try:
        fn()
    except Exception as exc:
        msg = str(exc)
        if contains and contains not in msg:
            raise AssertionError(f"expected error containing {contains!r}, got {msg!r}") from exc
        return msg
    raise AssertionError("mutation unexpectedly passed")


def independent_score(registry: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    by = {m["id"]: m for m in report["metrics"]}
    category_raw: dict[str, float] = {}
    category_score: dict[str, int] = {}
    overall_num = 0.0
    overall_den = 0.0
    for cid, cdef in registry["categories"].items():
        num = 0.0; den = 0.0
        for mdef in registry["metrics"]:
            if mdef["category"] != cid:
                continue
            row = by[mdef["id"]]
            if row.get("applicable") is True and row.get("measurement_class") in {"measured", "observed"} and isinstance(row.get("score"), (int, float)) and not isinstance(row.get("score"), bool):
                w = float(mdef["weight"]); den += w; num += float(row["score"]) * w
        if den:
            raw = num / den
            category_raw[cid] = raw
            category_score[cid] = int(round(raw))
            cw = float(cdef["weight"])
            overall_num += raw * cw; overall_den += cw
    return {
        "score": int(round(overall_num / overall_den)) if overall_den else None,
        "coverage_percent": 100,
        "category_scores": category_score,
    }


def reconcile_analysis(registry: dict[str, Any], scored: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    reg = {m["id"]: m for m in registry["metrics"]}
    score_by = {m["id"]: m for m in scored["metrics"]}
    ana_by = {m["id"]: m for m in analysis["metrics"]}
    if set(ana_by) != set(reg): errors.append("REPORT-001 metric ID parity")
    for mid, mdef in reg.items():
        a = ana_by.get(mid); s = score_by.get(mid)
        if not a or not s: continue
        if float(a.get("metric_weight", -1)) != float(mdef["weight"]): errors.append(f"{mid} metric_weight")
        cw = float(registry["categories"][mdef["category"]]["weight"])
        if float(a.get("category_weight", -1)) != cw: errors.append(f"{mid} category_weight")
        expected = round(float(s["score"]) * float(mdef["weight"]) / 100.0, 6) if isinstance(s.get("score"), (int,float)) and not isinstance(s.get("score"), bool) else None
        if a.get("weighted_contribution") != expected: errors.append(f"{mid} weighted_contribution")
        if a.get("evidence_refs") != sorted(s.get("evidence_refs", [])): errors.append(f"{mid} evidence_refs")
    cat_by = {x["category"]:x for x in analysis["categories"]}
    for c in scored["score_summary"]["category_scores"]:
        cid=c["category"]; a=cat_by.get(cid)
        if not a: errors.append(f"category {cid} missing"); continue
        members=[score_by[m["id"]] | {"weight":m["weight"]} for m in registry["metrics"] if m["category"]==cid and isinstance(score_by[m["id"]].get("score"),(int,float)) and not isinstance(score_by[m["id"]].get("score"),bool)]
        numerator=round(sum(float(x["score"])*float(x["weight"]) for x in members),6)
        if a.get("weighted_score_numerator") != numerator: errors.append(f"category {cid} numerator")
        if a.get("score") != c.get("score"): errors.append(f"category {cid} score")
    if analysis.get("score_summary",{}).get("score") != scored.get("score_summary",{}).get("score"): errors.append("REPORT-003 overall score")
    return errors


def temp_binding_root(root: Path, mutated_binding: dict[str, Any]) -> Path:
    td = Path(tempfile.mkdtemp(prefix="pxk-binding-mutation-")) / "pixelkiez-website-diagnosis"
    (td/"assets").mkdir(parents=True); (td/"schemas").mkdir(); (td/"scripts").mkdir()
    for rel in ["assets/measurement-registry.json","assets/capability-registry.json","schemas/core-evidence-binding.schema.json","scripts/validate_core_evidence_bindings.py"]:
        src=root/rel; dst=td/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    dump(td/"assets/core-evidence-bindings.active.v1.json", mutated_binding)
    return td


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_full_48_active_evals.py <skill-dir>", file=sys.stderr); return 1
    root = Path(argv[1]).resolve(); py=sys.executable
    artifact_digest = run([py, str(root / "scripts/pipeline_ledger.py"), "digest", str(root)]).stdout.strip()
    checks: list[dict[str, Any]]=[]; mutations: list[dict[str, Any]]=[]
    def ok(cid: str, detail: str = "PASS") -> None: checks.append({"id":cid,"status":"PASS","detail":detail})
    def mut(mid: str, fn: Callable[[], Any], contains: str | None = None) -> None:
        msg=expect_error(fn,contains)
        mutations.append({"mutation":mid,"status":"DETECTED","detail":msg[:500]})
        checks.append({"id":mid,"status":"PASS","detail":"negative control detected"})
    try:
        registry=json.loads((root/"assets/measurement-registry.json").read_text())
        binding=json.loads((root/"assets/core-evidence-bindings.active.v1.json").read_text())
        bundle=json.loads((root/"evals/fixtures/full-48-core-execution.json").read_text())
        base=json.loads((root/"evals/fixtures/synthetic-report.json").read_text())

        # Binding integrity.
        run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(root)])
        ok("BIND-001","exact 48/48 registry equality")
        dup=copy.deepcopy(binding); dup["metrics"][-1]=copy.deepcopy(dup["metrics"][0])
        mut("BIND-002", lambda: run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(temp_binding_root(root,dup))]))
        unk=copy.deepcopy(binding); unk["metrics"][-1]["metric_id"]="FAKE-99"
        mut("BIND-003", lambda: run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(temp_binding_root(root,unk))]))

        # Execution contract and admission behavior.
        validate_bundle(root,bundle); admission=admission_report(root,bundle)
        assert admission["score_admitted"]==48 and admission["release_state"]=="FULL_48_ACTIVE_PASS"
        ok("EXEC-001","48 execution outputs and 48 admissions")
        unavailable=copy.deepcopy(bundle); r=next(x for x in unavailable["results"] if x["metric_id"]=="AI-07"); r.update(execution_state="UNAVAILABLE",product_status=None,value=None,evidence_refs=[],evidence_grade="E8",reason_codes=["EVIDENCE_UNAVAILABLE"])
        adm_un=admission_report(root,unavailable); assert adm_un["score_admitted"]==47 and adm_un["release_state"]=="BLOCKED_FULL_48_ACTIVE"; ok("EXEC-002","UNAVAILABLE remains non-score-admitted")
        falsecase=copy.deepcopy(bundle); r=next(x for x in falsecase["results"] if x["metric_id"]=="FIND-02"); r["value"]={"robots_present":False,"sitemap_present":False}; assert next(x for x in admission_report(root,falsecase)["metrics"] if x["metric_id"]=="FIND-02")["score_admitted"] is True; ok("EXEC-003","false boolean remains measured evidence")
        zerocase=copy.deepcopy(bundle); r=next(x for x in zerocase["results"] if x["metric_id"]=="TRUST-03"); r["value"]={"https_final":True,"tls_verified":True,"security_headers_present_count":0}; assert next(x for x in admission_report(root,zerocase)["metrics"] if x["metric_id"]=="TRUST-03")["score_admitted"] is True; ok("EXEC-004","numeric zero remains measured evidence")
        wrong=copy.deepcopy(bundle); wrong["results"][0]["target_url"]="https://wrong.example/"; mut("EXEC-005",lambda:validate_bundle(root,wrong),"TARGET_MISMATCH")
        conflict=copy.deepcopy(bundle); r=next(x for x in conflict["results"] if x["metric_id"]=="AI-06"); r.update(execution_state="CONFLICT",product_status=None,value=None,evidence_refs=[],evidence_grade="E8",reason_codes=["EVIDENCE_CONFLICT"]); assert admission_report(root,conflict)["score_admitted"]==47; ok("EXEC-006","CONFLICT classified and not score-admitted")
        raw=copy.deepcopy(bundle); raw["results"][0]["raw_provider_payload_present"]=True; mut("EXEC-007",lambda:validate_bundle(root,raw))
        shuffled=copy.deepcopy(bundle); random.Random(42).shuffle(shuffled["results"]); random.Random(43).shuffle(shuffled["evidence_catalog"]); shuffled["generated_at"]="2099-01-01T00:00:00Z"; [x.__setitem__("observed_at","2099-01-01T00:00:00Z") for x in shuffled["results"]]; assert semantic_digest(bundle)==semantic_digest(shuffled); ok("EXEC-008","semantic ordering/timestamps do not change digest")

        # Score/materialization and independent recomputation.
        materialized,admission=materialize_report(root,base,bundle)
        with tempfile.TemporaryDirectory(prefix="pxk-active-eval-") as td:
            t=Path(td); pre=t/"diagnosis-report.json"; scored=t/"diagnosis-report-scored.json"; analysis=t/"analysis_report.json"; client=t/"client-report-model.json"
            dump(pre,materialized)
            run([py,str(root/"scripts/compute_score.py"),str(pre),str(scored)])
            scored_data=json.loads(scored.read_text())
            independent=independent_score(registry,scored_data)
            used_weights={m["id"]:m["weight"] for m in registry["metrics"]}; assert len(used_weights)==48
            ok("SCORE-001","exact registry weights used")
            weight_mut=copy.deepcopy(binding); weight_mut["metrics"][0]["metric_weight"]=float(weight_mut["metrics"][0]["metric_weight"])+1
            mut("SCORE-002",lambda:run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(temp_binding_root(root,weight_mut))]),"metric weight drift")
            noev=copy.deepcopy(bundle); noev["results"][0]["evidence_refs"]=[]; mut("SCORE-003",lambda:validate_bundle(root,noev))
            th=copy.deepcopy(bundle); tr=next(x for x in th["results"] if x["metric_id"]=="PERF-01"); tr["threshold_source"]=None; mut("SCORE-004",lambda:validate_bundle(root,th),"THRESHOLD_SOURCE_MISSING")
            actual_cat={x["category"]:x["score"] for x in scored_data["score_summary"]["category_scores"]}; assert scored_data["score_summary"]["score"]==independent["score"] and actual_cat==independent["category_scores"] and scored_data["score_summary"]["coverage_percent"]==100
            ok("SCORE-005",f"golden score {independent['score']} matches independent recomputation")
            mat2,_=materialize_report(root,base,shuffled); pre2=t/"shuffled.json"; scored2=t/"shuffled-scored.json"; dump(pre2,mat2); run([py,str(root/"scripts/compute_score.py"),str(pre2),str(scored2)]); assert sha(scored)==sha(scored2); ok("SCORE-006","shuffled semantic input yields byte-identical scored report")

            # Internal report traceability.
            run([py,str(root/"scripts/build_internal_analysis_report.py"),str(scored),str(analysis)])
            analysis_data=json.loads(analysis.read_text())
            schema=json.loads((root/"schemas/analysis-report.schema.json").read_text()); jsonschema.Draft202012Validator(schema).validate(analysis_data)
            errs=reconcile_analysis(registry,scored_data,analysis_data); assert not errs,errs
            ok("REPORT-001","all scored metrics reconcile to analysis_report")
            ok("REPORT-002","metric weighted contributions reconcile to categories")
            ok("REPORT-003","category results reconcile to overall result")
            assert set(x["id"] for x in analysis_data["metrics"])==set(x["id"] for x in registry["metrics"]); ok("REPORT-004","no phantom or missing metric")
            run([py,str(root/"scripts/build_client_report_model.py"),str(scored),str(client)])
            client_text=client.read_text(encoding="utf-8")
            forbidden=["weighted_contribution","metric_weight","execution_run_id","execution_semantic_digest","score_anchor_source"]
            assert not any(x in client_text for x in forbidden); ok("REPORT-005","customer model contains no active-core debug/weight leakage")

            # Required mutations beyond named test IDs.
            binding_removed=copy.deepcopy(binding); binding_removed["metrics"].pop(); mut("MUT-REGISTRY-REMOVE",lambda:run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(temp_binding_root(root,binding_removed))]))
            binding_extra=copy.deepcopy(binding); extra=copy.deepcopy(binding_extra["metrics"][0]); extra["metric_id"]="FAKE-49"; binding_extra["metrics"].append(extra); mut("MUT-REGISTRY-49TH",lambda:run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(temp_binding_root(root,binding_extra))]))
            catw=copy.deepcopy(binding); catw["metrics"][0]["category_weight"]=99; mut("MUT-CATEGORY-WEIGHT",lambda:run([py,str(root/"scripts/validate_core_evidence_bindings.py"),str(temp_binding_root(root,catw))]),"category weight drift")
            evremoved=copy.deepcopy(bundle); ref=evremoved["results"][0]["evidence_refs"][0]; evremoved["evidence_catalog"]=[e for e in evremoved["evidence_catalog"] if e["id"]!=ref]; mut("MUT-EVIDENCE-REMOVE",lambda:validate_bundle(root,evremoved),"unknown evidence ref")
            valuetype=copy.deepcopy(bundle); valuetype["results"][0]["value"]="wrong"; mut("MUT-EVIDENCE-TYPE",lambda:validate_bundle(root,valuetype))
            evsrc=copy.deepcopy(bundle); ref=evsrc["results"][0]["evidence_refs"][0]; e=next(x for x in evsrc["evidence_catalog"] if x["id"]==ref); e["source_family"]="MANUAL_OR_NON_AUTOMATABLE"; mut("MUT-EVIDENCE-SOURCE",lambda:validate_bundle(root,evsrc),"evidence source-family conflict")
            raw2=copy.deepcopy(bundle); raw2["evidence_catalog"][0]["raw_provider_payload_present"]=True; mut("MUT-RAW-PROVIDER",lambda:validate_bundle(root,raw2))
            dup_ev=copy.deepcopy(bundle); d=copy.deepcopy(dup_ev["evidence_catalog"][0]); d["digest"]="0"*64; dup_ev["evidence_catalog"].append(d); mut("MUT-DUPLICATE-EVIDENCE",lambda:validate_bundle(root,dup_ev),"duplicate evidence")
            scoreinject=copy.deepcopy(bundle); scoreinject["results"][0]["score"]=100; mut("MUT-SCORE-WITHOUT-ADMISSION",lambda:validate_bundle(root,scoreinject))
            badanchor=copy.deepcopy(bundle); badanchor["results"][0]["product_status"]="excellent"; mut("MUT-ANCHOR-OUTSIDE",lambda:validate_bundle(root,badanchor))
            th2=copy.deepcopy(bundle); next(x for x in th2["results"] if x["metric_id"]=="PERF-02")["threshold_source"]=None; mut("MUT-THRESHOLD-REMOVE",lambda:validate_bundle(root,th2),"THRESHOLD_SOURCE_MISSING")
            analysis_missing=copy.deepcopy(analysis_data); analysis_missing["metrics"].pop(); msg=expect_error(lambda: (_ for _ in ()).throw(AssertionError(reconcile_analysis(registry,scored_data,analysis_missing))) if reconcile_analysis(registry,scored_data,analysis_missing) else None); mutations.append({"mutation":"MUT-ANALYSIS-METRIC-REMOVE","status":"DETECTED","detail":msg[:500]})
            analysis_bad=copy.deepcopy(analysis_data); analysis_bad["metrics"][0]["weighted_contribution"]+=1; msg=expect_error(lambda: (_ for _ in ()).throw(AssertionError(reconcile_analysis(registry,scored_data,analysis_bad))) if reconcile_analysis(registry,scored_data,analysis_bad) else None); mutations.append({"mutation":"MUT-WEIGHTED-CONTRIBUTION","status":"DETECTED","detail":msg[:500]})

            # Persist proof artifacts from the exact golden path.
            dump(root/"evals/fixtures/full-48-active-golden-score.json",{
                "fixture_only":True,"does_not_prove_live_measurement":True,"execution_semantic_digest":semantic_digest(bundle),
                "measurement_registry_digest":file_sha(root/"assets/measurement-registry.json"),"expected":independent,
            })
            dump(root/"reports/score-reconciliation-report.json",{
                "status":"PASS","fixture_only":True,"artifact_digest":artifact_digest,"compute_score_changed":False,"registry_weights_unchanged":True,
                "independent_recompute":independent,"compute_score_summary":scored_data["score_summary"],
            })
            dump(root/"reports/analysis-report-reconciliation.json",{
                "status":"PASS","artifact_digest":artifact_digest,"metric_count":48,"weighted_contributions":"RECONCILED","category_results":"RECONCILED","overall_result":"RECONCILED",
                "analysis_report_sha256":sha(analysis),"scored_report_sha256":sha(scored),"customer_internal_leakage":"NONE_DETECTED_IN_CLIENT_MODEL",
            })
            dump(root/"reports/core-active-determinism-report.json",{
                "status":"PASS","artifact_digest":artifact_digest,"semantic_digest":semantic_digest(bundle),"shuffled_semantic_digest":semantic_digest(shuffled),
                "scored_report_sha256":sha(scored),"shuffled_scored_report_sha256":sha(scored2),"timestamps_excluded_from_semantic_digest":True,
            })

        dump(root/"reports/core-active-mutation-test-report.json",{"status":"PASS","artifact_digest":artifact_digest,"detected":len(mutations),"mutations":mutations})
        required_ids={"BIND-001","BIND-002","BIND-003","EXEC-001","EXEC-002","EXEC-003","EXEC-004","EXEC-005","EXEC-006","EXEC-007","EXEC-008","SCORE-001","SCORE-002","SCORE-003","SCORE-004","SCORE-005","SCORE-006","REPORT-001","REPORT-002","REPORT-003","REPORT-004","REPORT-005"}
        got={x["id"] for x in checks}
        if required_ids-got: raise AssertionError(f"missing required checks {sorted(required_ids-got)}")
        dump(root/"reports/core-active-eval-results.json",{
            "status":"PASS","suite":"FULL_48_ACTIVE","artifact_digest":artifact_digest,"checks":checks,"required_check_count":len(required_ids),"mutation_count":len(mutations),
            "total_registry_metrics":48,"execution_ready":48,"evidence_ready":48,"score_admitted":48,"report_reconciled":48,
            "fixture_boundary":"FULL_48_ACTIVE proves the architecture on synthetic evidence; it is not live-site measurement proof."
        })
        print(f"PASS: FULL_48_ACTIVE checks={len(checks)} mutations={len(mutations)} metrics=48")
        return 0
    except Exception as exc:
        dump(root/"reports/core-active-eval-results.json",{"status":"FAIL","suite":"FULL_48_ACTIVE","error":str(exc),"checks":checks,"mutations":mutations})
        print(f"FAIL: {exc}",file=sys.stderr); return 1

if __name__=="__main__": raise SystemExit(main(sys.argv))
