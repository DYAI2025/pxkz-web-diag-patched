#!/usr/bin/env python3
"""Validate route catalog parity and methodology; never equate registration with execution."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

KNOWN_ADAPTERS={"PUBLIC_HTTP","PUBLIC_BROWSER","PUBLIC_CRUX","PAGESPEED_API","LIGHTHOUSE_CLI","PUBLIC_SEARCH","MANUAL_EVIDENCE","OWNER_EXPORT"}
KNOWN_CLASSES={"observation","qualitative_observation","manual_observation","lab_observation","lab","field","private_field","search_snapshot"}
KNOWN_IMPLEMENTATION={"IMPLEMENTED","PARTIAL_RAW_ONLY","CONDITIONAL_RUNTIME","MISSING_CORE_ADAPTER","MISSING_MACHINE_COLLECTOR","MISSING_AXE_OR_BRIDGE","EXISTING_NONCORE_ONLY","AUTH_REQUIRED_NONCORE_ONLY"}


def load_checked(root: Path, catalog_path: Path | None = None) -> dict:
    read=lambda r:json.loads((root/r).read_text(encoding="utf-8"))
    reg=read("assets/measurement-registry.json")
    bind=read("assets/core-evidence-bindings.active.v1.json")
    caps=read("assets/capability-registry.json")
    catalog=json.loads((catalog_path or root/"assets/metric-execution-routes.v1.json").read_text(encoding="utf-8"))
    regids=[m["id"] for m in reg["metrics"]]
    bindids=[m["metric_id"] for m in bind["metrics"]]
    if len(regids)!=48 or len(set(regids))!=48 or len(set(bindids))!=48 or set(regids)!=set(bindids):
        raise ValueError("REGISTRY_BINDING_PARITY_FAIL")
    routes=catalog.get("metrics",[])
    mids=[r.get("metric_id") for r in routes]
    if len(routes)!=48 or len(set(mids))!=48 or set(mids)!=set(regids):
        raise ValueError("ROUTE_REGISTRY_PARITY_FAIL: 48 unique registry IDs required")
    if catalog.get("registry_version")!=reg["registry_version"] or catalog.get("binding_contract_version")!=bind["contract_version"]:
        raise ValueError("ROUTE_VERSION_MISMATCH")
    by_reg={m["id"]:m for m in reg["metrics"]}
    by_bind={m["metric_id"]:m for m in bind["metrics"]}
    by_cap={c["id"]:c for c in caps["capabilities"]}
    if len(by_cap)!=14: raise ValueError("CAPABILITY_COUNT_DRIFT")
    allids=[]
    for route in routes:
        mid=route["metric_id"]; r=by_reg[mid]; b=by_bind[mid]
        if route.get("capability_id")!=r["capability_id"] or route.get("capability_id")!=b["capability_id"]:
            raise ValueError(f"{mid}: CAPABILITY_DRIFT")
        if route.get("registry_test_method")!=r["test_method"] or route.get("control_basis")!=r["control_basis"]:
            raise ValueError(f"{mid}: TEST_METHOD_DRIFT")
        if route.get("accepted_source_families")!=b["accepted_source_families"]:
            raise ValueError(f"{mid}: SOURCE_FAMILY_DRIFT")
        if route.get("permission_boundary")!=by_cap[r["capability_id"]]["permission"]:
            raise ValueError(f"{mid}: PERMISSION_DRIFT")
        if route.get("max_evidence_grade")!=r["max_evidence_grade"]:
            raise ValueError(f"{mid}: EVIDENCE_GRADE_DRIFT")
        if route.get("threshold_source_required")!=b["threshold_source_required"]:
            raise ValueError(f"{mid}: THRESHOLD_DRIFT")
        for x in [route.get("primary"), *(route.get("alternatives") or [])]:
            if not isinstance(x,dict): raise ValueError(f"{mid}: missing route")
            allids.append(x.get("route_id"))
            if x.get("method_id") in (None,"") or x.get("method_version") in (None,""):
                raise ValueError(f"{mid}: method identity missing")
            if x.get("source_family") not in b["accepted_source_families"]:
                raise ValueError(f"{mid}: UNAUTHORIZED_SOURCE_FAMILY")
            if x.get("adapter") not in KNOWN_ADAPTERS or x.get("measurement_class") not in KNOWN_CLASSES:
                raise ValueError(f"{mid}: UNSUPPORTED_ADAPTER_OR_MEASUREMENT_CLASS")
            if x.get("implementation_status") not in KNOWN_IMPLEMENTATION:
                raise ValueError(f"{mid}: IMPLEMENTATION_STATUS_UNDECLARED")
            if len(x.get("expected_inputs") or [])<3 or not isinstance(x.get("limits"),dict):
                raise ValueError(f"{mid}: INPUTS_OR_LIMITS_UNDECLARED")
            if x.get("permission") not in {"public_read_only","manual_authorized","owner_authorized"}:
                raise ValueError(f"{mid}: INVALID_PERMISSION")
            if x.get("adapter")=="OWNER_EXPORT" and x["permission"]!="owner_authorized":
                raise ValueError(f"{mid}: OWNER_PERMISSION_REQUIRED")
        slots=route.get('unavailable_fallback_slots')
        if not isinstance(slots,list) or len(slots)!=3-len(route.get('alternatives') or []):
            raise ValueError(f"{mid}: UNACCOUNTED_FALLBACK_SLOTS")
        if any(not s.get('reason') or s.get('reason') in {'UNKNOWN','MISSING'} for s in slots):
            raise ValueError(f"{mid}: FALLBACK_UNAVAILABILITY_NOT_EXPLAINED")
        ids=[m["method_id"] for m in [route["primary"],*(route.get("alternatives") or [])]]
        if len(ids)!=len(set(ids)) or len(route.get("alternatives") or [])>3:
            raise ValueError(f"{mid}: DUPLICATE_FALLBACK_OR_TOO_MANY")
        primary_class=route["primary"]["measurement_class"]
        for alt in route.get("alternatives") or []:
            if alt["measurement_class"]!=primary_class and alt.get("score_equivalence") not in {"NOT_EQUIVALENT_FOR_RENDERED_CLAIMS","RUBRIC_REVIEW_REQUIRED"}:
                raise ValueError(f"{mid}: FIELD_LAB_OR_RUBRIC_SUBSTITUTION")
        if r["capability_id"]=="performance_field":
            if any(m["measurement_class"]!="field" for m in [route["primary"],*(route.get("alternatives") or [])]):
                raise ValueError(f"{mid}: FIELD_LAB_SUBSTITUTION")
        if r["capability_id"]=="performance_lab":
            if any(m["measurement_class"]!="lab" for m in [route["primary"],*(route.get("alternatives") or [])]):
                raise ValueError(f"{mid}: FIELD_LAB_SUBSTITUTION")
        if route.get("not_applicable_rule") is not None:
            raise ValueError(f"{mid}: unsupported not-applicable rule; define tested rule first")
    if len(allids)!=len(set(allids)): raise ValueError("DUPLICATE_ROUTE_ID")
    return catalog


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('root');ap.add_argument('--catalog');args=ap.parse_args()
    try:
        c=load_checked(Path(args.root).resolve(),Path(args.catalog).resolve() if args.catalog else None)
        print(f"PASS: registered_routes={len(c['metrics'])} capabilities=14")
        return 0
    except Exception as e:
        print(f"FAIL: {e}",file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
