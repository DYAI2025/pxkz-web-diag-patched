#!/usr/bin/env python3
"""Validate security-boundary documentation and reject obvious embedded secrets."""
from __future__ import annotations
import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
]
TERMS = ["Permission boundary", "Data classification", "Forbidden behavior", "Rate, retry, and stop", "URL safety", "Audit trail"]

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_security_patterns.py <skill-dir>", file=sys.stderr); return 1
    root = Path(argv[1])
    policy = root / "references/security-and-tools.md"
    if not policy.is_file(): print("FAIL: security policy missing", file=sys.stderr); return 1
    policy_text = policy.read_text(encoding="utf-8")
    missing = [term for term in TERMS if term not in policy_text]
    if missing: print("FAIL: security terms missing: " + ", ".join(missing), file=sys.stderr); return 1
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".yaml", ".json"}: continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            print(f"FAIL: possible secret in {path.relative_to(root)}", file=sys.stderr); return 1
    print("PASS: security boundary and secret scan")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

