#!/usr/bin/env python3
"""Probe: do swapped/permuted finding.metric_refs (same measured values) change customer levers?

Runs the real builder CLIs (compute_score -> build_visualization_plan -> build_client_report_model
--visual-plan --claim-bindings-out -> validate_customer_claim_bindings -> validate_customer_surface_consistency)
in an archive copy of candidate d95ad75, proof semantics (no customer-mode synthetic block involved: the
builders themselves have no release-mode switch; build_audit_deliverables passes --release-mode only to its own
synthetic gate).

Usage: swap_probe.py <skill_root> <work_dir>
"""
from __future__ import annotations

import copy
import itertools
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
WORK = Path(sys.argv[2]).resolve()
WORK.mkdir(parents=True, exist_ok=True)
PY = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))
from customer_status import customer_status  # noqa: E402
from strategic_relevance import evaluate_finding  # noqa: E402

REG = {m["id"]: m for m in json.loads((ROOT / "assets/measurement-registry.json").read_text())["metrics"]}
COUNTER = itertools.count()


def run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-B", *map(str, cmd)], capture_output=True, text=True, cwd=ROOT)


def must(cmd: list) -> subprocess.CompletedProcess:
    p = run(cmd)
    if p.returncode != 0:
        raise SystemExit(f"FAIL {cmd}\n{p.stdout}\n{p.stderr}")
    return p


def write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def pipeline(pre: dict, tag: str) -> dict:
    d = WORK / f"{next(COUNTER):03d}-{tag}"
    d.mkdir(parents=True, exist_ok=True)
    src = write(d / "input.json", pre)
    scored = d / "scored.json"
    must([ROOT / "scripts/compute_score.py", src, scored])
    plan, model, bind = d / "plan.json", d / "model.json", d / "bindings.json"
    p_plan = run([ROOT / "scripts/build_visualization_plan.py", scored, plan])
    if p_plan.returncode != 0:
        return {"dir": d.name, "plan_rc": p_plan.returncode, "plan_err": (p_plan.stdout + p_plan.stderr).strip()[-300:]}
    p_model = run([ROOT / "scripts/build_client_report_model.py", scored, model, "--visual-plan", plan, "--claim-bindings-out", bind])
    if p_model.returncode != 0:
        return {"dir": d.name, "plan_rc": 0, "model_rc": p_model.returncode, "model_err": (p_model.stdout + p_model.stderr).strip()[-300:]}
    p_cb = run([ROOT / "scripts/validate_customer_claim_bindings.py", scored, model, bind])
    p_gate = run([ROOT / "scripts/validate_customer_surface_consistency.py", scored, plan, model, bind])
    P, M, B = (json.loads(x.read_text()) for x in (plan, model, bind))
    vis = [v for v in P["visuals"] if v.get("status", "SELECTED") == "SELECTED"]
    return {
        "dir": d.name,
        "levers": [f["id"] for f in M["findings"]],
        "plan_top_levers": P.get("top_levers"),
        "strengths": M["executive"]["strengths"],
        "admitted": sorted(c["finding_ref"] for c in B["claims"] if c.get("admitted") and c.get("finding_ref")),
        "roadmap": [(b, i["finding_ref"]) for b in ("now", "next_30_days", "next_quarter") for i in M["roadmap"][b]],
        "closing": M["closing"]["actions"],
        "selected_visuals": [v["template_id"] for v in vis],
        "matrix_rows": {v["template_id"]: [(r.get("metric_ref"), r.get("status")) for r in v.get("data", [])]
                        for v in vis if v["template_id"] in {"V08_AI_ANSWERABILITY", "V10_TRUST_MATRIX"}},
        "threshold_finding": [v.get("finding_refs") for v in vis if v["template_id"] == "V07_PERFORMANCE_THRESHOLD"],
        "numeric_signal": {f["id"]: (f.get("numeric_signal") or {}).get("metric_ref") for f in M["findings"]},
        "specificity_basis": {f["id"]: f.get("specificity_basis") for f in M["findings"]},
        "claim_bindings_rc": p_cb.returncode,
        "gate_rc": p_gate.returncode,
        "gate_out": (p_gate.stdout + p_gate.stderr).strip().splitlines(),
    }


CUSTOMER_KEYS = ("levers", "plan_top_levers", "strengths", "admitted", "roadmap", "closing", "selected_visuals",
                 "matrix_rows", "threshold_finding", "gate_rc", "gate_out", "claim_bindings_rc")
AUX_KEYS = ("numeric_signal", "specificity_basis")


def diff(base: dict, mut: dict) -> dict:
    out = {}
    for k in CUSTOMER_KEYS + AUX_KEYS + ("plan_rc", "plan_err", "model_rc", "model_err"):
        if base.get(k) != mut.get(k):
            out[k] = {"baseline": base.get(k), "mutated": mut.get(k)}
    return out


def primary_key(scored_report: dict, finding: dict) -> str | None:
    """Selector's primary reading (client_story.contradicted_by_clear_metrics definition)."""
    v = evaluate_finding(scored_report, finding)
    if v.get("evidence_route") != "CORE_METRIC":
        return None
    metrics = {m["id"]: m for m in scored_report["metrics"]}
    assessed = set(v.get("linked_assessed_metrics", []))
    linked = [metrics[x] for x in finding.get("metric_refs", []) if x in assessed and x in metrics]
    return f"{linked[0]['id']}:{customer_status(linked[0])['key']}" if linked else None


def scored_of(res: dict) -> dict:
    return json.loads((WORK / res["dir"] / "scored.json").read_text())


def explain(base_res: dict, mut_res: dict) -> dict:
    """Which findings changed their selector-primary reading (documented B4 rule)."""
    if "dir" not in base_res or "dir" not in mut_res:
        return {}
    sb, sm = scored_of(base_res), scored_of(mut_res)
    fm = {f["id"]: f for f in sm["findings"]}
    out = {}
    for f in sb["findings"]:
        if f.get("severity") == "positive":
            continue
        a, b = primary_key(sb, f), primary_key(sm, fm[f["id"]])
        # Only a change of the primary READING (not merely of its id) can legitimately change admission.
        if (a or "").split(":")[-1] != (b or "").split(":")[-1]:
            out[f["id"]] = {"baseline_primary": a, "mutated_primary": b}
    return out


def report(label: str, base: dict, mut: dict) -> dict:
    d = diff(base, mut)
    cust = {k: v for k, v in d.items() if k not in AUX_KEYS}
    rec = {"mutation": label, "customer_fields_changed": sorted(cust), "aux_changed": sorted(k for k in d if k in AUX_KEYS),
           "levers_baseline": base.get("levers"), "levers_mutated": mut.get("levers"),
           "primary_changes": explain(base, mut), "detail": d}
    print(json.dumps({k: rec[k] for k in ("mutation", "customer_fields_changed", "aux_changed", "levers_baseline", "levers_mutated", "primary_changes")},
                     ensure_ascii=False))
    for k in sorted(cust):
        print("   ", k, json.dumps(d[k], ensure_ascii=False)[:600])
    return rec


def value_key(m: dict) -> tuple:
    return (m.get("score"), m.get("status"), m.get("measurement_class"), m.get("evidence_grade"), m.get("confidence"), m.get("unit"))


def fixtures() -> dict[str, dict]:
    fx = ROOT / "evals/fixtures"
    out = {"synthetic": json.loads((fx / "synthetic-report.json").read_text())}
    consistent = json.loads((fx / "active-positive-consistent-findings.v1.json").read_text())
    active_input = copy.deepcopy(out["synthetic"])
    for key in ("findings", "roadmap", "options", "visualizations", "executive_summary"):
        active_input[key] = consistent[key]
    src = write(WORK / "active.input.json", active_input)
    mat = WORK / "active.materialized.json"
    must([ROOT / "scripts/materialize_core_metrics.py", ROOT, src, fx / "full-48-core-execution.json", mat,
          "--admission-out", WORK / "active.admission.json"])
    out["active"] = json.loads(mat.read_text())
    return out


def scored_metrics(pre: dict) -> dict:
    tmp = write(WORK / "_tmp_in.json", pre)
    must([ROOT / "scripts/compute_score.py", tmp, WORK / "_tmp_scored.json"])
    return {m["id"]: m for m in json.loads((WORK / "_tmp_scored.json").read_text())["metrics"]}


def main() -> int:
    records: list[dict] = []
    for name, pre in fixtures().items():
        print(f"\n===== FIXTURE {name}")
        base = pipeline(pre, f"{name}-baseline")
        print("BASELINE", json.dumps({k: base.get(k) for k in ("levers", "strengths", "admitted", "roadmap", "gate_rc", "gate_out", "matrix_rows", "numeric_signal")}, ensure_ascii=False))
        base_again = pipeline(pre, f"{name}-baseline-rerun")
        print("DETERMINISM baseline==rerun:", diff(base, base_again) == {})
        mets = scored_metrics(pre)

        # (a) reverse metric_refs of every finding at once.
        m = copy.deepcopy(pre)
        for f in m["findings"]:
            f["metric_refs"] = list(reversed(f.get("metric_refs", [])))
        records.append({"fixture": name, **report("a:reverse-all", base, pipeline(m, f"{name}-a-reverse-all"))})
        # (a) every non-identity permutation of one finding at a time (others unchanged).
        for i, f0 in enumerate(pre["findings"]):
            refs = f0.get("metric_refs", [])
            if len(refs) < 2:
                continue
            for perm in itertools.permutations(refs):
                if list(perm) == refs:
                    continue
                m = copy.deepcopy(pre)
                m["findings"][i]["metric_refs"] = list(perm)
                same_vals = len({value_key(mets[r]) for r in refs}) == 1
                lab = f"a:perm {f0['id']} {refs}->{list(perm)} identical_values={same_vals}"
                records.append({"fixture": name, **report(lab, base, pipeline(m, f"{name}-a-{f0['id']}-{'_'.join(perm)}"))})

        # (b) two findings swap one cited id each; the two metrics have identical score/status/class/grade/confidence/unit,
        # and their value fields are equalized in BOTH baseline' and mutation so only the id differs.
        cited = [(i, r) for i, f in enumerate(pre["findings"]) for r in f.get("metric_refs", [])]
        pairs = []
        for (i, a), (j, b) in itertools.combinations(cited, 2):
            if i == j or a == b or a in pre["findings"][j]["metric_refs"] or b in pre["findings"][i]["metric_refs"]:
                continue
            if value_key(mets[a]) != value_key(mets[b]) or mets[a].get("measurement_class") == "not_assessed":
                continue
            same_cat = REG[a]["category"] == REG[b]["category"]
            pairs.append((i, a, j, b, same_cat))
        print(f"(b) candidate identical-value pairs cited by two different findings: {len(pairs)} "
              f"(same category: {sum(p[4] for p in pairs)}, different category: {sum(not p[4] for p in pairs)})")
        for i, a, j, b, same_cat in pairs:
            eq = copy.deepcopy(pre)
            # Equalize value payload so the swap changes only the id the finding cites.
            ma = next(x for x in eq["metrics"] if x["id"] == a)
            mb = next(x for x in eq["metrics"] if x["id"] == b)
            mb["value"] = ma.get("value")
            base_eq = pipeline(eq, f"{name}-b-eqbase-{a}-{b}")
            sw = copy.deepcopy(eq)
            fi, fj = sw["findings"][i], sw["findings"][j]
            fi["metric_refs"] = [b if r == a else r for r in fi["metric_refs"]]
            fj["metric_refs"] = [a if r == b else r for r in fj["metric_refs"]]
            lab = (f"b:swap {fi['id']}({pre['findings'][i]['severity']}) {a}->{b} / {fj['id']}({pre['findings'][j]['severity']}) {b}->{a} "
                   f"{'same' if same_cat else 'diff'}-category {REG[a]['category']}/{REG[b]['category']} key={value_key(mets[a])}")
            records.append({"fixture": name, "same_category": same_cat, **report(lab, base_eq, pipeline(sw, f"{name}-b-{a}-{b}"))})

    fx = fixtures()
    # (b') single-sided replacement: a finding cites an UNCITED metric with identical score/status/class/grade/confidence
    # (value equalized in baseline' and mutation), same and different category, including topic-overlap ids.
    print("\n===== (b') single-sided identical-value id replacement")
    for name, fid, a, b in (
        ("synthetic", "F-004", "FIND-08", "FIND-07"),   # lever, same category findability_seo
        ("synthetic", "F-002", "PERF-07", "PERF-04"),   # lever, same category performance_technology (measured)
        ("synthetic", "F-002", "PERF-07", "A11Y-04"),   # lever, different category (measured)
        ("synthetic", "F-001", "UX-04", "UX-05"),       # lever, same category; UX-05 in topic group form_burden
        ("synthetic", "F-001", "UX-04", "UX-01"),       # lever, same category
        ("active", "F-104", "FIND-04", "PERF-09"),      # lever, different category
        ("active", "F-103", "A11Y-02", "FIND-09"),      # lever, different category; FIND-09 in topic group image_alternatives
        ("active", "F-103", "A11Y-02", "TRUST-01"),     # lever, different category; TRUST-01 presence_only, in V10 matrix
        ("active", "F-108", "UX-02", "UX-07"),          # positive (strength), same category; UX-07 in headings group with lever A11Y-02
        ("active", "F-108", "UX-02", "AI-05"),          # positive (strength), different category; AI-05 in proof group with TRUST-06
    ):
        pre = fx[name]
        mets = scored_metrics(pre)
        assert value_key(mets[a]) == value_key(mets[b]), (a, b, value_key(mets[a]), value_key(mets[b]))
        eq = copy.deepcopy(pre)
        next(x for x in eq["metrics"] if x["id"] == b)["value"] = next(x for x in eq["metrics"] if x["id"] == a).get("value")
        base_eq = pipeline(eq, f"{name}-bp-eqbase-{a}-{b}")
        sw = copy.deepcopy(eq)
        f = next(x for x in sw["findings"] if x["id"] == fid)
        f["metric_refs"] = [b if r == a else r for r in f["metric_refs"]]
        same = REG[a]["category"] == REG[b]["category"]
        lab = f"b':replace {fid}({f['severity']}) {a}->{b} {'same' if same else 'diff'}-category key={value_key(mets[a])}"
        records.append({"fixture": name, "same_category": same, **report(lab, base_eq, pipeline(sw, f"{name}-bp-{a}-{b}"))})

    # (c) order within one finding where the refs do NOT read the same (positive control for the probe) and the
    # selector-vs-gate primary definitions (inferred_risk / presence_only).
    print("\n===== (c) primary-rule positive control and selector-vs-gate definitions (synthetic)")
    pre = fx["synthetic"]
    base = pipeline(pre, "c-baseline")

    def variant(tag: str, refs: list[str], tweak=None) -> None:
        m = copy.deepcopy(pre)
        if tweak:
            tweak(m)
        next(x for x in m["findings"] if x["id"] == "F-001")["metric_refs"] = refs
        records.append({"fixture": "synthetic", **report(f"c:{tag} F-001 refs={refs}", base, pipeline(m, "c-" + tag + "-" + "_".join(refs)))})

    variant("control-action-first", ["UX-02", "TRUST-03"])
    variant("control-clear-first", ["TRUST-03", "UX-02"])

    def inferred(m: dict) -> None:
        next(x for x in m["metrics"] if x["id"] == "PERF-01").update(
            {"measurement_class": "inferred_risk", "status": "not_assessed", "score": None})
    variant("inferred-first", ["PERF-01", "TRUST-03"], inferred)
    variant("inferred-second", ["TRUST-03", "PERF-01"], inferred)
    variant("presence-only-first", ["TRUST-01", "UX-02"])
    variant("presence-only-second", ["UX-02", "TRUST-01"])

    (WORK / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=1))
    print("\n===== SUMMARY")
    bad = []
    for r in records:
        lever_changed = r["levers_baseline"] != r["levers_mutated"]
        unexplained = lever_changed and not r["primary_changes"]
        idv = "identical_values=True" in r["mutation"] or r["mutation"].startswith("b:")
        if unexplained or (idv and r["customer_fields_changed"]):
            bad.append(r["mutation"])
    print("records:", len(records))
    print("lever-set/order changed:", sum(r["levers_baseline"] != r["levers_mutated"] for r in records))
    print("lever change WITHOUT a selector-primary reading change:", sum((r["levers_baseline"] != r["levers_mutated"]) and not r["primary_changes"] for r in records))
    print("identical-value mutations with any customer-field change:", [ (r["fixture"], r["mutation"], r["customer_fields_changed"]) for r in records
          if ("identical_values=True" in r["mutation"] or r["mutation"].startswith("b:")) and r["customer_fields_changed"]])
    print("candidates for BUG:", bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
