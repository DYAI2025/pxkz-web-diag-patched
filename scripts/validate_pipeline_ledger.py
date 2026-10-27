#!/usr/bin/env python3
"""Validate the Pixelkiez build ledger and required ordered build stages."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REQUIRED = [
    "INTAKE_COMPLETED",
    "RESEARCH_COMPLETED",
    "CAPABILITY_DECISION_SKIPPED",
    "ARCHITECTURE_GATE_PASSED",
    "DRAFT_FROZEN",
    "RELEASE_GATE_PASSED",
    "EVALUATOR_PASSED",
    "VALIDATION_PASSED",
    "PACKAGE_AUTHORIZED",
]


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_pipeline_ledger.py <skill-dir>")
    root = Path(argv[1]).resolve()
    module_path = root / "scripts/pipeline_ledger.py"
    spec = importlib.util.spec_from_file_location("pk_pipeline_ledger", module_path)
    if spec is None or spec.loader is None:
        return fail("cannot load pipeline ledger module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ledger = root / "reports/build-events.jsonl"
    try:
        events = module.read_events(ledger)
        ok, reason = module.verify(events, module.digest_tree(root))
    except Exception as exc:
        return fail(str(exc))
    if not ok:
        return fail(reason)
    types = [event.get("event_type") for event in events]
    if types != REQUIRED:
        return fail("required build stage sequence missing or out of order")
    if len({event.get("run_id") for event in events}) != 1:
        return fail("ledger must use one run_id")
    freeze_digest = events[4].get("artifact_digest")
    if not freeze_digest:
        return fail("DRAFT_FROZEN must carry artifact digest")
    for event in events[5:]:
        if event.get("artifact_digest") != freeze_digest:
            return fail(f"post-freeze digest mismatch: {event.get('event_type')}")
    print("PASS: build pipeline ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
