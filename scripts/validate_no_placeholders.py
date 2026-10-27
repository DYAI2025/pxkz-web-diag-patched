#!/usr/bin/env python3
"""Detect unresolved generation placeholders without mistaking Python f-strings for placeholders."""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOUBLE = re.compile(r"\{\{[A-Z_][A-Z0-9_]*\}\}")
SINGLE = re.compile(r"\{[A-Z_][A-Z0-9_]*\}")
TODO = re.compile(r"\[TODO:")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json"}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_no_placeholders.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    hits: list[str] = []
    for path in root.rglob("*"):
        if path.resolve() == Path(__file__).resolve() or not path.is_file():
            continue
        if set(path.relative_to(root).parts) & {"reports", "evals", "__pycache__"}:
            continue
        if path.suffix not in TEXT_SUFFIXES and path.suffix != ".py" and path.name != "SKILL.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        patterns = (TODO, DOUBLE) if path.suffix == ".py" else (TODO, DOUBLE, SINGLE)
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append(f"{path.relative_to(root)}:{match.group(0)}")
    if hits:
        print("FAIL: unresolved placeholders: " + ", ".join(sorted(set(hits))), file=sys.stderr)
        return 1
    print("PASS: no unresolved production placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
