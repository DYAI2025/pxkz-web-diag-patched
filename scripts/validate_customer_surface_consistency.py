#!/usr/bin/env python3
"""Fail closed when two customer surfaces read the same metric or the same order differently.

Usage: validate_customer_surface_consistency.py <scored-report.json> <visualization-plan.json> <client-report-model.json>
       <customer-claim-bindings.json>

Probe checklist B1-B6 and C2/C4 (docs/plans/2026-10-29-customer-pdf-qa-probe-checklist.md). Every check recomputes the
expected customer reading from the scored report with customer_reading.py instead of trusting the builders.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from customer_reading import contested_metrics, metric_reading, overlap_blocked, primary_metric, registry_defs  # noqa: E402
from customer_status import STATUS_META  # noqa: E402

MATRICES = {"V08_AI_ANSWERABILITY": "question", "V10_TRUST_MATRIX": "signal"}
BUCKETS = ("now", "next_30_days", "next_quarter")


def load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(value: object) -> str:
    return " ".join(str(value or "").split())


def check(report: dict[str, Any], plan: dict[str, Any], model: dict[str, Any], bindings: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    defs = registry_defs()
    metrics = {str(m.get("id")): m for m in report.get("metrics", []) if isinstance(m, dict)}
    reading = {mid: metric_reading(report, defs, m) for mid, m in metrics.items()}
    source_findings = {str(f.get("id")): f for f in report.get("findings", []) if isinstance(f, dict)}
    lever_ids = [str(f.get("id")) for f in model.get("findings", []) if isinstance(f, dict)]
    lever_metrics = {str(x) for fid in lever_ids for x in source_findings.get(fid, {}).get("metric_refs", []) or []}
    blocked = overlap_blocked(report, lever_metrics, defs)
    visuals = [v for v in plan.get("visuals", []) if isinstance(v, dict) and v.get("status", "SELECTED") == "SELECTED"]

    # B2: an admitted strength cites only metrics reading "Klar" and no topic-overlapped metric.
    for claim in bindings.get("claims", []) or []:
        if not isinstance(claim, dict) or not claim.get("admitted"):
            continue
        refs = [str(x) for x in claim.get("metric_refs", []) or []]
        if not refs:
            errors.append(f"STRENGTH_NOT_CLEAR: {claim.get('finding_ref')} has no metric")
        for ref in refs:
            if reading.get(ref, {}).get("key") != "CLEAR":
                errors.append(f"STRENGTH_NOT_CLEAR: {claim.get('finding_ref')} cites {ref} reading "
                              f"{reading.get(ref, {}).get('label', 'unknown')}")
            if ref in blocked:
                errors.append(f"STRENGTH_TOPIC_OVERLAP: {claim.get('finding_ref')} cites {ref}")
    admitted = {norm(c.get("text")) for c in bindings.get("claims", []) or [] if isinstance(c, dict) and c.get("admitted")}
    for text in model.get("executive", {}).get("strengths", []) or []:
        if norm(text) not in admitted:
            errors.append(f"STRENGTH_NOT_CLEAR: shown strength without admitted binding: {text}")

    # B1/B3: every matrix row shows the metric's one reading; lever metrics may read IMPROVE instead of CLEAR.
    for v in visuals:
        if v.get("template_id") not in MATRICES:
            continue
        for row in v.get("data", []) or []:
            mid = str(row.get("metric_ref"))
            expected = reading.get(mid)
            if expected is None:
                errors.append(f"MATRIX_READING_MISMATCH: {v['template_id']} row {mid} has no scored metric")
                continue
            allowed = {expected["label"]}
            if expected["key"] == "CLEAR" and mid in lever_metrics:
                allowed = {STATUS_META["IMPROVE"]["label"]}
            if row.get("status") not in allowed:
                errors.append(f"MATRIX_READING_MISMATCH: {v['template_id']} {mid} shows {row.get('status')!r}, reading is {sorted(allowed)}")
            if row.get("status") == STATUS_META["CLEAR"]["label"] and mid in blocked:
                errors.append(f"MATRIX_TOPIC_OVERLAP: {v['template_id']} {mid} reads Klar next to a flagged topic")
            if expected["present"] and "(vorhanden)" not in str(row.get(MATRICES[v["template_id"]], "")):
                errors.append(f"MATRIX_READING_MISMATCH: {mid} is a present presence check without '(vorhanden)'")

    # B4: no lever whose primary assessed metric reads "Klar".
    for fid in lever_ids:
        primary = primary_metric(report, source_findings.get(fid, {}))
        if primary is not None and reading[str(primary.get("id"))]["key"] == "CLEAR":
            errors.append(f"LEVER_PRIMARY_CLEAR: {fid} primary metric {primary.get('id')} reads Klar")

    # B5: no category bar for an area containing a contested metric.
    contested_categories = {str(defs.get(mid, {}).get("category")) for mid in contested_metrics(report) if mid in defs}
    for v in visuals:
        if v.get("template_id") == "V02_CATEGORY_BARS":
            shown = {str(r).split(":", 1)[1] for r in v.get("metric_refs", []) if str(r).startswith("CATEGORY:")}
            for cat in sorted(shown & contested_categories):
                errors.append(f"CONTESTED_CATEGORY_BAR: {cat}")

    # B6: the threshold page only illustrates a lever.
    for v in visuals:
        if v.get("template_id") == "V07_PERFORMANCE_THRESHOLD":
            for fid in v.get("finding_refs", []) or []:
                if str(fid) not in lever_ids:
                    errors.append(f"THRESHOLD_NOT_A_LEVER: {fid}")

    # C2/C4: one execution order; every lever scheduled exactly once; no P1/P2 labels.
    roadmap = model.get("roadmap", {})
    items = [i for b in BUCKETS for i in roadmap.get(b, []) or [] if isinstance(i, dict)]
    order = [str(i.get("finding_ref")) for i in items]
    for i in items:
        if "priority" in i:
            errors.append(f"PRIORITY_LABEL_SHOWN: {i.get('finding_ref')} {i.get('priority')}")
    for fid in lever_ids:
        if order.count(fid) != 1:
            errors.append(f"LEVER_NOT_SCHEDULED: {fid} appears {order.count(fid)} times in the roadmap")
    lever_action = {str(f.get("id")): norm(f.get("action")) for f in model.get("findings", []) if isinstance(f, dict)}
    expected_closing = [lever_action.get(fid, "") for fid in order]
    if [norm(x) for x in model.get("closing", {}).get("actions", [])] != expected_closing:
        errors.append("EXECUTION_ORDER_MISMATCH: closing actions do not follow the roadmap order")
    if items and norm(model.get("recommendation", {}).get("next_step")) != norm(items[0].get("action")):
        errors.append("EXECUTION_ORDER_MISMATCH: next step is not the first roadmap item")
    return errors


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__.strip().splitlines()[2])
        return 2
    report, plan, model, bindings = (load(p) for p in sys.argv[1:5])
    errors = check(report, plan, model, bindings)
    for e in errors:
        print(f"FAIL: {e}")
    if errors:
        return 1
    print("PASS: customer surfaces share one reading per metric and one execution order")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
