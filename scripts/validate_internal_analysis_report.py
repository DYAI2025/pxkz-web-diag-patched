#!/usr/bin/env python3
"""Validate internal JSON/Markdown completeness against the canonical scored report."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator


def fail(message: str) -> int:
    print("FAIL: " + message, file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        return fail("usage: validate_internal_analysis_report.py <analysis.json> <canonical-report.json> <analysis.md>")
    analysis_path, canonical_path, markdown_path = map(lambda x: Path(x).resolve(), argv[1:])
    root = Path(__file__).resolve().parents[1]
    try:
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        schema = json.loads((root / "schemas/analysis-report.schema.json").read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errors:
            return fail("schema: " + errors[0].message)
        digest = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
        if data.get("source_report_sha256") != digest:
            return fail("analysis report is stale against canonical report")
        expected = [str(x.get("id")) for x in canonical.get("metrics", [])]
        observed = [str(x.get("id")) for x in data.get("metrics", [])]
        if observed != expected:
            return fail("metric order/set mismatch")
        if len(observed) != len(set(observed)):
            return fail("duplicate metric IDs")
        if data.get("sources", []) != canonical.get("sources", []):
            return fail("source register mismatch")
        allowed_actions = {str(x.get("id")) for x in data.get("recommendations", [])}
        for metric in data.get("metrics", []):
            if not metric.get("interpretation") or not metric.get("does_not_prove") or not metric.get("source_or_method"):
                return fail(f"metric completeness missing: {metric.get('id')}")
            if any(ref not in allowed_actions for ref in metric.get("recommendation_refs", [])):
                return fail(f"unknown recommendation ref: {metric.get('id')}")
        markdown = markdown_path.read_text(encoding="utf-8")
        for metric_id in expected:
            count = markdown.count(f"`{metric_id}`")
            anchor_count = markdown.count(f'<a id="metric-{metric_id.lower()}"></a>')
            if count != 1 or anchor_count != 1:
                return fail(f"markdown metric occurrence/anchor {metric_id}={count}/{anchor_count}, expected 1/1")
        for source in canonical.get("sources", []):
            sid = str(source.get("id") or "")
            if sid and markdown.count(f"### {sid}:") != 1:
                return fail(f"markdown source occurrence {sid} != 1")
        print(f"PASS: internal analysis complete metrics={len(expected)} json+markdown")
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
