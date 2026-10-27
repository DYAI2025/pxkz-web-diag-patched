#!/usr/bin/env python3
"""Validate agent-portability disclosure."""
from __future__ import annotations
import json
import sys
from pathlib import Path

def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr); return 1

def main(argv: list[str]) -> int:
    if len(argv) != 2: return fail("usage: validate_agent_agnostic.py <skill-dir>")
    root = Path(argv[1])
    ref = root / "references/agent-agnostic-compatibility.md"
    try: report = json.loads((root / "reports/agent-compatibility-report.json").read_text(encoding="utf-8"))
    except Exception as exc: return fail(f"invalid compatibility report: {exc}")
    if not ref.is_file(): return fail("compatibility reference missing")
    if report.get("identical_cross_platform_behavior_guaranteed") is not False: return fail("cross-platform behavior must not be guaranteed")
    if not report.get("runtime_specific_dependencies") or not report.get("unverified_runtimes"): return fail("runtime differences missing")
    print("PASS: agent compatibility disclosures")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

