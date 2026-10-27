#!/usr/bin/env python3
"""Validate source map and source policy controls."""
from __future__ import annotations
import sys
from pathlib import Path

TERMS = ["type:", "purpose:", "reliability:", "limitations:", "confidence_default:", "user_provided", "primary", "SOURCE_NEEDED", "MISSING"]

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_source_map.py <skill-dir>", file=sys.stderr); return 1
    root = Path(argv[1])
    paths = [root / "references/source-map.md", root / "references/source-policy.md"]
    if not all(path.exists() for path in paths):
        print("FAIL: source map or policy missing", file=sys.stderr); return 1
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    missing = [term for term in TERMS if term not in text]
    if missing:
        print("FAIL: missing source terms: " + ", ".join(missing), file=sys.stderr); return 1
    print("PASS: source map and policy")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

