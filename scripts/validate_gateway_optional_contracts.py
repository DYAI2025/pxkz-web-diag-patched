#!/usr/bin/env python3
"""Validate provider-neutral future monitoring/analytics contracts."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_gateway_optional_contracts.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    try:
        monitoring = json.loads((root / "schemas/availability-monitoring.schema.json").read_text(encoding="utf-8"))
        analytics = json.loads((root / "schemas/owner-analytics.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(monitoring)
        Draft202012Validator.check_schema(analytics)
        one_shot = {"schema_version":"1.0","target_url":"https://example.com/","state":"AVAILABLE","period":None,"samples":[],"incidents":[],"provider":"","evidence_class":"NOT_ASSESSED"}
        Draft202012Validator(monitoring).validate(one_shot)
        if one_shot["evidence_class"] == "CONTINUOUS_MONITORING":
            raise ValueError("one-shot fixture cannot assert continuous monitoring")
        no_history = {"schema_version":"1.0","target_url":"https://example.com/","state":"NOT_CONFIGURED","provider":"","date_range":None,"metrics":[],"instrumentation_state":"NOT_INSTRUMENTED","permission_state":"NOT_AUTHORIZED"}
        Draft202012Validator(analytics).validate(no_history)
        print("PASS: optional monitoring/owner-analytics contracts")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
