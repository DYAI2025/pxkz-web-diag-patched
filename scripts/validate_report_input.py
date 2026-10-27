#!/usr/bin/env python3
"""Validate a scored Pixelkiez diagnosis report and truth-discipline invariants."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema

from chart_contract import validate_visualizations

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_DIR / "schemas" / "diagnosis-report.schema.json"
REGISTRY_PATH = SKILL_DIR / "assets" / "measurement-registry.json"
CAPABILITY_PATH = SKILL_DIR / "assets" / "capability-registry.json"
MONEY_OR_PERCENT = re.compile(r"(?:[$€£]|\b(?:EUR|USD)\b|\d+(?:[.,]\d+)?\s*%)", re.I)
GUARANTEE = re.compile(r"\b(?:guaranteed?|guarantees?|garantiert|zwangsläufig|certain to|wird sicher)\b", re.I)
SCOREABLE_CLASSES = {"measured", "observed"}


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_report_input.py <report.json>")
    try:
        report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cap_registry = json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(report)
    except Exception as exc:
        return fail(f"schema validation failed: {exc}")

    errors: list[str] = []
    errors.extend(validate_visualizations(report.get("visualizations", [])))
    metric_defs = {m.get("id"): m for m in registry.get("metrics", []) if isinstance(m, dict)}
    metric_ids = set(metric_defs)
    seen_metrics: set[str] = set()

    cap_ids = {c.get("id") for c in cap_registry.get("capabilities", []) if isinstance(c, dict)}
    cap_status: dict[str, str] = {}
    for row in report.get("coverage", {}).get("capabilities", []):
        cid = row.get("id")
        if cid not in cap_ids:
            errors.append(f"unknown capability {cid}")
            continue
        if cid in cap_status:
            errors.append(f"duplicate capability {cid}")
        cap_status[str(cid)] = str(row.get("status"))
    missing_caps = sorted(cap_ids - set(cap_status))
    if missing_caps:
        errors.append("missing capability states: " + ", ".join(missing_caps))

    anchors = registry.get("metric_score_scale", {})
    for m in report.get("metrics", []):
        mid = m.get("id")
        if mid not in metric_ids:
            errors.append(f"unknown metric {mid}")
            continue
        if mid in seen_metrics:
            errors.append(f"duplicate metric {mid}")
        seen_metrics.add(mid)
        mdef = metric_defs[mid]
        applicable = m.get("applicable") is True
        measurement_class = m.get("measurement_class")
        status = m.get("status")
        score = m.get("score")
        if not applicable:
            if status != "not_applicable" or score is not None:
                errors.append(f"{mid} not applicable must use not_applicable and null score")
            continue
        if measurement_class == "not_assessed" and status != "not_assessed":
            errors.append(f"{mid} not_assessed must use not_assessed status")
        if measurement_class in {"inferred_risk", "not_assessed"} and score is not None:
            errors.append(f"{mid} cannot score measurement_class={measurement_class}")
        if m.get("evidence_grade") in {"E7", "E8"} and score is not None:
            errors.append(f"{mid} cannot score evidence grade {m.get('evidence_grade')}")
        capability_id = mdef.get("capability_id")
        if measurement_class in SCOREABLE_CLASSES and cap_status.get(str(capability_id)) != "available":
            errors.append(f"{mid} uses {measurement_class} while capability {capability_id} is not available")
        if score is not None:
            expected = anchors.get(status)
            if expected is None or float(score) != float(expected):
                errors.append(f"{mid} score must equal product anchor for status {status}")
            if mdef.get("score_mode") == "external_threshold" and not m.get("threshold_source"):
                errors.append(f"{mid} external-threshold score requires threshold_source")

    missing_metrics = sorted(metric_ids - seen_metrics)
    if missing_metrics:
        errors.append("report must contain every registry metric row: " + ", ".join(missing_metrics))

    evidence_ids: set[str] = set()
    finding_ids: set[str] = set()
    for f in report.get("findings", []):
        fid = f.get("id")
        if fid in finding_ids:
            errors.append(f"duplicate finding {fid}")
        finding_ids.add(fid)
        for ev in f.get("evidence", []):
            eid = ev.get("id")
            if eid in evidence_ids:
                errors.append(f"duplicate evidence {eid}")
            evidence_ids.add(eid)
        if f.get("severity") in {"critical", "high", "medium"} and not f.get("evidence"):
            errors.append(f"{fid} adverse finding requires evidence")
        if not f.get("client_observation") or not f.get("client_impact") or not f.get("client_action"):
            errors.append(f"{fid} requires client_observation/client_impact/client_action")
        rel = f.get("business_relevance", {})
        if rel.get("classification") == "inference" and GUARANTEE.search(str(rel.get("text", ""))):
            errors.append(f"{fid} inference contains guarantee language")
        if not f.get("recommendation", {}).get("acceptance_test"):
            errors.append(f"{fid} requires acceptance_test")

    for viz in report.get("visualizations", []):
        for mid in viz.get("metric_refs", []):
            if mid not in metric_ids:
                errors.append(f"{viz.get('id')} references unknown metric {mid}")
        ref = viz.get("finding_ref")
        if ref is not None and ref not in finding_ids:
            errors.append(f"{viz.get('id')} references unknown finding {ref}")

    score = report.get("score_summary", {})
    if score.get("registry_version") != registry.get("registry_version"):
        errors.append("score registry_version does not match current measurement registry")
    if score.get("policy_version") != "2.0.0":
        errors.append("score policy_version must be 2.0.0")
    coverage = int(score.get("coverage_percent", 0))
    if coverage < 50 and score.get("score") is not None:
        errors.append("overall score must be hidden below 50% coverage")
    if coverage >= 80 and score.get("display_status") != "FULL_SCORE":
        errors.append("coverage >=80 must use FULL_SCORE")
    if 50 <= coverage < 80 and score.get("display_status") != "PARTIAL_SCORE":
        errors.append("coverage 50-79 must use PARTIAL_SCORE")
    caveats = " ".join(str(x).lower() for x in score.get("does_not_prove", []))
    if "univers" not in caveats or not any(x in caveats for x in ["ranking", "umsatz", "conversion", "revenue"]):
        errors.append("score caveats must reject universal and business-outcome interpretations")

    for horizon in report.get("scenario_horizons", []):
        for path in horizon.get("paths", []) if isinstance(horizon, dict) else []:
            text = str(path.get("outcome", ""))
            if MONEY_OR_PERCENT.search(text):
                errors.append("future scenario contains unsupported money or percentage")
            if GUARANTEE.search(text):
                errors.append("future scenario contains guarantee language")

    if not report.get("sources"):
        errors.append("sources must not be empty")
    if not report.get("limitations"):
        errors.append("limitations must not be empty")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: report input ({len(report.get('metrics', []))} metrics, {len(report.get('findings', []))} findings, coverage {coverage}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
