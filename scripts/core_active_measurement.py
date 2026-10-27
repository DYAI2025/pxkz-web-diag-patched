#!/usr/bin/env python3
"""Deterministic active-core evidence admission and canonical metric materialization."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

GRADE_RANK = {f"E{i}": i for i in range(1, 9)}
SCOREABLE = {"MEASURED": "measured", "OBSERVED": "observed"}
NON_SCORE_REASON = {
    "UNAVAILABLE": "EVIDENCE_UNAVAILABLE",
    "ERROR": "EXECUTION_ERROR",
    "CONFLICT": "EVIDENCE_CONFLICT",
    "NOT_APPLICABLE": "NOT_APPLICABLE",
}

class ContractError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    evid=[]
    for e in bundle.get("evidence_catalog", []):
        evid.append({k:e.get(k) for k in (
            "id","source_family","target_url","status","evidence_grade","digest","reference","claim_boundary","raw_provider_payload_present"
        )})
    results=[]
    for r in bundle.get("results", []):
        results.append({
            "metric_id":r.get("metric_id"), "target_url":r.get("target_url"), "source_family":r.get("source_family"),
            "execution_state":r.get("execution_state"), "evidence_grade":r.get("evidence_grade"), "value":r.get("value"),
            "unit":r.get("unit"), "evidence_refs":sorted(r.get("evidence_refs", [])), "source_or_method":r.get("source_or_method"),
            "limitation":r.get("limitation"), "product_status":r.get("product_status"), "threshold_source":r.get("threshold_source"),
            "confidence":r.get("confidence"), "reason_codes":sorted(r.get("reason_codes", [])), "note":r.get("note"),
            "raw_provider_payload_present":r.get("raw_provider_payload_present"),
        })
    return {
        "schema_version":bundle.get("schema_version"),
        "binding_contract_version":bundle.get("binding_contract_version"),
        "target_url":bundle.get("target_url"),
        "mode":bundle.get("mode"),
        "evidence_catalog":sorted(evid,key=lambda x:str(x.get("id"))),
        "results":sorted(results,key=lambda x:str(x.get("metric_id"))),
    }


def semantic_digest(bundle: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_semantic_bundle(bundle)))


def load_contracts(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    registry=load_json(root/"assets/measurement-registry.json")
    caps=load_json(root/"assets/capability-registry.json")
    bindings=load_json(root/"assets/core-evidence-bindings.active.v1.json")
    schema=load_json(root/"schemas/core-execution-bundle.schema.json")
    return registry,caps,bindings,schema


def validate_bundle(root: Path, bundle: dict[str, Any]) -> None:
    registry,caps,bindings,schema=load_contracts(root)
    try:
        jsonschema.Draft202012Validator(schema).validate(bundle)
    except Exception as exc:
        raise ContractError(str(exc)) from exc
    reg_by={m["id"]:m for m in registry["metrics"]}
    bind_by={b["metric_id"]:b for b in bindings["metrics"]}
    result_ids=[r["metric_id"] for r in bundle["results"]]
    if len(result_ids)!=48 or len(set(result_ids))!=48 or set(result_ids)!=set(reg_by):
        raise ContractError("execution bundle must contain exactly the 48 registry metric IDs once each")
    evidence_ids=[e["id"] for e in bundle["evidence_catalog"]]
    if len(evidence_ids)!=len(set(evidence_ids)):
        raise ContractError("conflicting duplicate evidence id")
    ev_by={e["id"]:e for e in bundle["evidence_catalog"]}
    target=bundle["target_url"]
    for r in bundle["results"]:
        mid=r["metric_id"]; b=bind_by[mid]
        if r["target_url"]!=target:
            raise ContractError(f"{mid}: TARGET_MISMATCH")
        if r["raw_provider_payload_present"] is not False:
            raise ContractError(f"{mid}: RAW_PROVIDER_EVIDENCE_REJECTED")
        if r["source_family"] not in b["accepted_source_families"]:
            raise ContractError(f"{mid}: source family {r['source_family']} is not authorized")
        state=r["execution_state"]
        if state in SCOREABLE:
            if state not in b["required_evidence"]["scoreable_execution_states"]:
                raise ContractError(f"{mid}: execution state {state} not allowed by capability contract")
            if not isinstance(r["value"],dict):
                raise ContractError(f"{mid}: VALUE_TYPE_INVALID")
            grade=r["evidence_grade"]
            if GRADE_RANK.get(grade,99)>GRADE_RANK.get(b["maximum_evidence_grade"],6):
                raise ContractError(f"{mid}: EVIDENCE_GRADE_TOO_WEAK")
            if r["product_status"] not in b["allowed_score_statuses"]:
                raise ContractError(f"{mid}: unauthorized product status")
            if not r["source_or_method"].strip(): raise ContractError(f"{mid}: method missing")
            if not r["limitation"].strip(): raise ContractError(f"{mid}: limitation missing")
            if b["threshold_source_required"] and not (r.get("threshold_source") or "").strip():
                raise ContractError(f"{mid}: THRESHOLD_SOURCE_MISSING")
            if not r["evidence_refs"]:
                raise ContractError(f"{mid}: evidence reference missing")
            referenced=[]
            for ref in r["evidence_refs"]:
                if ref not in ev_by: raise ContractError(f"{mid}: unknown evidence ref {ref}")
                e=ev_by[ref]; referenced.append(e)
                if e["target_url"]!=target: raise ContractError(f"{mid}: evidence TARGET_MISMATCH")
                if e["raw_provider_payload_present"] is not False: raise ContractError(f"{mid}: RAW_PROVIDER_EVIDENCE_REJECTED")
                if e["source_family"]!=r["source_family"]: raise ContractError(f"{mid}: evidence source-family conflict")
                if e["status"] not in {"MEASURED","OBSERVED"}: raise ContractError(f"{mid}: non-scoreable evidence state {e['status']}")
                if GRADE_RANK.get(e["evidence_grade"],99)>GRADE_RANK.get(b["maximum_evidence_grade"],6):
                    raise ContractError(f"{mid}: evidence grade exceeds metric maximum")
            weakest=max(GRADE_RANK[e["evidence_grade"]] for e in referenced)
            if GRADE_RANK[grade] < weakest:
                raise ContractError(f"{mid}: result evidence grade overstates referenced evidence")
        else:
            expected=NON_SCORE_REASON.get(state)
            if expected and expected not in r["reason_codes"]:
                raise ContractError(f"{mid}: non-scoreable state must include reason {expected}")


def admission_report(root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    validate_bundle(root,bundle)
    registry,_,bindings,_=load_contracts(root)
    bind_by={b["metric_id"]:b for b in bindings["metrics"]}
    anchors=registry["metric_score_scale"]
    rows=[]; admitted=0
    result_by={r["metric_id"]:r for r in bundle["results"]}
    for m in registry["metrics"]:
        mid=m["id"]; r=result_by[mid]; b=bind_by[mid]
        ok=r["execution_state"] in SCOREABLE
        if ok: admitted+=1
        rows.append({
            "metric_id":mid,
            "category":m["category"],
            "metric_weight":m["weight"],
            "category_weight":registry["categories"][m["category"]]["weight"],
            "source_family":r["source_family"],
            "execution_state":r["execution_state"],
            "evidence_grade":r["evidence_grade"],
            "evidence_refs":sorted(r["evidence_refs"]),
            "threshold_source":r.get("threshold_source"),
            "score_admitted":ok,
            "product_status":r["product_status"] if ok else None,
            "score":anchors[r["product_status"]] if ok else None,
            "reason_codes":[] if ok else list(r["reason_codes"]),
            "score_anchor_source":"assets/measurement-registry.json#metric_score_scale",
            "control_basis":b["control_basis"],
            "normalization_path":b["normalization_path"],
        })
    return {
        "schema_version":"1.0",
        "target_url":bundle["target_url"],
        "execution_run_id":bundle["execution_run_id"],
        "mode":bundle["mode"],
        "binding_contract_version":bindings["contract_version"],
        "measurement_registry_version":registry["registry_version"],
        "binding_digest":file_sha(root/"assets/core-evidence-bindings.active.v1.json"),
        "measurement_registry_digest":file_sha(root/"assets/measurement-registry.json"),
        "execution_semantic_digest":semantic_digest(bundle),
        "total_registry_metrics":48,
        "execution_results":48,
        "score_admitted":admitted,
        "metrics":rows,
        "release_state":"FULL_48_ACTIVE_PASS" if admitted==48 else "BLOCKED_FULL_48_ACTIVE",
    }


def materialize_report(root: Path, base_report: dict[str, Any], bundle: dict[str, Any]) -> tuple[dict[str, Any],dict[str, Any]]:
    admission=admission_report(root,bundle)
    registry,caps,_,_=load_contracts(root)
    result_by={r["metric_id"]:r for r in bundle["results"]}
    anchor=registry["metric_score_scale"]
    metrics=[]
    for m in registry["metrics"]:
        r=result_by[m["id"]]; state=r["execution_state"]
        if state in SCOREABLE:
            metric={
                "id":m["id"],"applicable":True,"measurement_class":SCOREABLE[state],"evidence_grade":r["evidence_grade"],
                "status":r["product_status"],"value":copy.deepcopy(r["value"]),"unit":r["unit"],"score":anchor[r["product_status"]],
                "confidence":r["confidence"],"source_or_method":r["source_or_method"],"threshold_source":r["threshold_source"],
                "evidence_refs":sorted(r["evidence_refs"]),"does_not_prove":r["limitation"],"note":r.get("note"),
            }
        else:
            not_app=state=="NOT_APPLICABLE"
            metric={
                "id":m["id"],"applicable":not not_app,"measurement_class":"not_assessed","evidence_grade":"E8",
                "status":"not_applicable" if not_app else "not_assessed","value":copy.deepcopy(r["value"]),"unit":r["unit"],"score":None,
                "confidence":1,"source_or_method":r["source_or_method"],"threshold_source":None,
                "evidence_refs":sorted(r["evidence_refs"]),"does_not_prove":r["limitation"],
                "note":r.get("note") or ",".join(r["reason_codes"]),
            }
        metrics.append(metric)
    out=copy.deepcopy(base_report)
    out["metrics"]=metrics
    # Reconcile capability availability from execution truth; no scoreable metric may claim an unavailable capability.
    by_cap={c["id"]:[] for c in caps["capabilities"]}
    reg_by={m["id"]:m for m in registry["metrics"]}
    for mid,r in result_by.items(): by_cap[reg_by[mid]["capability_id"]].append(r["execution_state"])
    cap_rows=[]
    for c in caps["capabilities"]:
        states=by_cap[c["id"]]
        if any(s in SCOREABLE for s in states): status="available"
        elif states and all(s=="NOT_APPLICABLE" for s in states): status="not_applicable"
        else: status="unavailable"
        cap_rows.append({"id":c["id"],"status":status,"note":"derived from active core execution bundle"})
    coverage=out.setdefault("coverage",{})
    coverage["capabilities"]=cap_rows
    return out,admission
