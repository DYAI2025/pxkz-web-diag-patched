#!/usr/bin/env python3
"""Validate trigger and output eval coverage."""
from __future__ import annotations
import json
import sys
from pathlib import Path

def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr); return 1

def main(argv: list[str]) -> int:
    if len(argv) != 2: return fail("usage: validate_evals.py <skill-dir>")
    root = Path(argv[1])
    try:
        triggers = json.loads((root / "evals/trigger_queries.json").read_text(encoding="utf-8"))
        outputs = json.loads((root / "evals/output_evals.json").read_text(encoding="utf-8"))
    except Exception as exc: return fail(f"invalid eval JSON: {exc}")
    if not isinstance(triggers, list) or len(triggers) < 8: return fail("at least 8 trigger cases required")
    if sum(item.get("should_trigger") is True for item in triggers) < 3: return fail("at least 3 positive triggers required")
    if sum(item.get("should_trigger") is False for item in triggers) < 3: return fail("at least 3 negative or near-miss triggers required")
    if not isinstance(outputs, list) or len(outputs) < 5: return fail("at least 5 output evals required")
    for item in outputs:
        if not all(key in item for key in ("id", "prompt", "expected_properties", "failure_modes")): return fail("output eval missing required fields")
        if not item["expected_properties"] or not item["failure_modes"]: return fail("output eval properties and failure modes must be non-empty")
    print(f"PASS: evals ({len(triggers)} triggers, {len(outputs)} outputs)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

