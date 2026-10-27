#!/usr/bin/env python3
"""Fail closed if the Measurement Platform patch claims unresolved third-party source reuse."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ALLOWED_REUSE = {"NONE", "REFERENCE_ONLY", "REIMPLEMENT_CONCEPT"}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_third_party_license_ledger.py <skill-dir>", file=sys.stderr)
        return 1
    try:
        root = Path(argv[1]).resolve()
        data = json.loads((root / "reports/third-party-license-ledger.json").read_text(encoding="utf-8"))
        rows = data.get("repositories", [])
        if len(rows) != 4:
            raise ValueError("exactly four supplied repository snapshots must be recorded")
        for row in rows:
            if row.get("source_code_copied") is not False:
                raise ValueError(f"third-party source reuse is not approved: {row.get('repo_id')}")
            if row.get("reuse_mode") not in ALLOWED_REUSE:
                raise ValueError(f"unsupported reuse mode: {row.get('repo_id')}")
            if not row.get("snapshot_sha256"):
                raise ValueError(f"snapshot digest missing: {row.get('repo_id')}")
        print("PASS: third-party ledger 4 repositories; no source code copied")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
