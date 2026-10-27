#!/usr/bin/env python3
"""Validate batch_context types, field authority and selected contract binding."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_contract import DEFAULT_CONTRACT_VERSION, contract_path, sha256_file, load_contract  # noqa: E402
from build_elevenlabs_batch_csv import validate_context  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_context")
    parser.add_argument("--contract-version", choices=["v1", "v1.1", "v1.2", "v1.3"], default=DEFAULT_CONTRACT_VERSION)
    args = parser.parse_args(argv[1:] if argv is not None else None)
    try:
        data = json.loads(Path(args.batch_context).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("batch_context must be a JSON object")
        root = Path(__file__).resolve().parents[1]
        cpath = contract_path(args.contract_version, root)
        contract = load_contract(cpath)
        validate_context(contract, data, sha256_file(cpath))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: batch_context is contract-bound and authority-safe ({args.contract_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
