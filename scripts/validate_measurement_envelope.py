#!/usr/bin/env python3
"""Validate a Pixelkiez Measurement Gateway envelope."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_measurement_envelope.py <envelope.json>", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    try:
        payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        schema = json.loads((root / "schemas/measurement-envelope.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(payload)
        if payload.get("execution_mode") == "FIXTURE" and any(str(x.get("evidence_ref", "")).startswith("LIVE-") for x in payload.get("observations", []) if isinstance(x, dict)):
            raise ValueError("fixture envelope cannot carry LIVE evidence refs")
        if payload.get("status") in {"FAILED", "UNAVAILABLE"} and payload.get("observations"):
            raise ValueError("failed/unavailable envelope must not masquerade as successful observations")
        print(f"PASS: measurement envelope observations={len(payload.get('observations', []))} mode={payload.get('execution_mode')} status={payload.get('status')}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
