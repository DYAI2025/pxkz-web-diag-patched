#!/usr/bin/env python3
"""Attach a Vibe-Check #03 result to a scored diagnosis report (opt-in, non-scoring).

Embeds the validated VC03 block as `report.vibecheck03` and derives customer-
candidate findings from the versioned rule table
`assets/vibecheck03-customer-admission-rules.v1.json`. Customer copy comes only
from fixed templates and numeric observation values; page content is never
copied. Metrics, score and categories are left untouched. Re-running replaces
earlier VC03-derived findings (idempotent).

Usage: attach_vibecheck03_findings.py <scored-report.json> <vibecheck03.json> <output.json>
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from vibecheck03_admission import (EVIDENCE_TYPE, admission_summary, block_errors,
                                   is_vc03_finding, render_value, triggered_rules)

ROOT = Path(__file__).resolve().parents[1]
VC03_SCHEMA = ROOT / "schemas" / "vibecheck03-diagnostics.schema.json"
FIRST_ID = 930
__all__ = ["Vc03AttachError", "attach", "admission_summary"]


class Vc03AttachError(ValueError):
    """VC03 result cannot be bound to this report."""


def _next_id(prefix: str, taken: set[str], start: int) -> tuple[str, int]:
    n = start
    while f"{prefix}-{n:03d}" in taken:
        n += 1
    return f"{prefix}-{n:03d}", n + 1


def _fill(template: str, values: dict[str, Any], page_url: str) -> str:
    # Tokens: {page_url} and {value:METRIC_ID}; only observed numbers/booleans are inserted.
    def sub(match: re.Match[str]) -> str:
        if match.group(0) == "{page_url}":
            return page_url
        value = values[match.group(1)]
        return str(value).lower() if isinstance(value, bool) else str(value)

    return re.sub(r"\{page_url\}|\{value:([A-Z0-9_]+)\}", sub, template)


def attach(report: dict[str, Any], vc03: dict[str, Any]) -> dict[str, Any]:
    errors = sorted(Draft202012Validator(json.loads(VC03_SCHEMA.read_text(encoding="utf-8"))).iter_errors(vc03), key=str)
    if errors:
        raise Vc03AttachError(f"vibecheck03 schema: {errors[0].message}")
    binding = block_errors(report, vc03)
    if binding:
        raise Vc03AttachError("vibecheck03 result not bound to this report: " + ", ".join(binding))

    out = copy.deepcopy(report)
    out["vibecheck03"] = copy.deepcopy(vc03)
    kept = [f for f in out.get("findings", []) if not (isinstance(f, dict) and is_vc03_finding(f))]
    taken_f = {str(f.get("id")) for f in kept if isinstance(f, dict)}
    taken_e = {str(e.get("id")) for f in kept if isinstance(f, dict) for e in f.get("evidence", []) if isinstance(e, dict)}
    fid_n = eid_n = FIRST_ID
    page = vc03["page_url"]
    derived = []
    for rule, rows in triggered_rules(vc03):
        if not rule.get("customer_admission"):
            continue
        values = {m: r["value"] for m, r in rows.items()}
        evidence = []
        for metric in rule["evidence_metrics"]:
            row = rows[metric]
            eid, eid_n = _next_id("E", taken_e, eid_n)
            taken_e.add(eid)
            evidence.append({
                "id": eid, "type": EVIDENCE_TYPE,
                "detail": f"{row['evidence_ref']} = {render_value(row['value'])}",
                "url": page, "observed_at": row["observed_at"],
                "method": f"{row['method']} ({row['collector_version']})", "asset_path": None,
            })
        fid, fid_n = _next_id("F", taken_f, fid_n)
        taken_f.add(fid)
        c = rule["copy"]
        derived.append({
            "id": fid, "category": rule["category"], "title": c["title"], "severity": rule["severity"],
            "observation": _fill(c["observation"], values, page),
            "evidence": evidence,
            "business_relevance": {"classification": "inference", "text": c["business_relevance"]},
            "client_observation": _fill(c["client_observation"], values, page),
            "client_impact": c["client_impact"],
            "client_action": c["client_action"],
            "recommendation": {
                "action": c["recommendation_action"], "owner": c["owner"], "horizon": c["horizon"],
                "acceptance_test": _fill(rule["acceptance_test"], values, page),
            },
            "confidence": rule["confidence"],
            "visual_asset": None,
        })
    out["findings"] = kept + derived
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 1
    try:
        report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        vc03 = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        out = attach(report, vc03)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    Path(argv[3]).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = admission_summary(out) or {}
    eligible = [r["rule_id"] for r in summary.get("rules", []) if r["status"] == "ELIGIBLE"]
    print(f"PASS: vibecheck03 attached run={vc03['run_id']} eligible_findings={len(eligible)} score_effect=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
