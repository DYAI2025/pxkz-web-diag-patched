#!/usr/bin/env python3
"""Validate installability controls."""
from __future__ import annotations
import json
import sys
from pathlib import Path

def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr); return 1

def main(argv: list[str]) -> int:
    if len(argv) != 2: return fail("usage: validate_installability.py <skill-dir>")
    root = Path(argv[1])
    for rel in ("SKILL.md", "agents/openai.yaml", "references/installability-and-distribution.md", "reports/installability-report.json"):
        if not (root / rel).is_file(): return fail(f"missing {rel}")
    try: report = json.loads((root / "reports/installability-report.json").read_text(encoding="utf-8"))
    except Exception as exc: return fail(f"invalid report: {exc}")
    if report.get("artifact_name") != "skill.zip": return fail("artifact must be skill.zip")
    if report.get("chatgpt_install_ready") is not True: return fail("chatgpt_install_ready must be true for packaged release")
    if report.get("frontend_install_suggestion_status") not in {"prepared", "blocked", "not_controlled_by_skill"}: return fail("invalid frontend status")
    if "not_controlled_by_skill" not in report: return fail("runtime limits missing")
    if report.get("blocking_issues"): return fail("installability blockers remain")
    print("PASS: installability controls")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

