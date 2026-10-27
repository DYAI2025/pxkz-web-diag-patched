#!/usr/bin/env python3
"""Validate Pixelkiez ElevenLabs batch CSVs against supported v1 through v1.3 contracts."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_contract import contract_path, detect_contract_for_headers, headers, load_contract, parse_csv, sha256_file, validate_csv_row  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path")
    parser.add_argument("--contract-version", choices=["auto", "v1", "v1.1", "v1.2", "v1.3"], default="auto")
    parser.add_argument("--require-batch-ready", action="store_true", help="Backward-compatible alias for --require-elevenlabs-upload-ready.")
    parser.add_argument("--require-elevenlabs-upload-ready", action="store_true")
    parser.add_argument("--require-production-prerequisites", action="store_true")
    parser.add_argument("--json-out")
    args = parser.parse_args(argv[1:] if argv is not None else None)
    csv_path = Path(args.csv_path).resolve()
    root = Path(__file__).resolve().parents[1]
    try:
        csv_headers, rows, has_bom = parse_csv(csv_path)
        if args.contract_version == "auto":
            selector, cpath, contract = detect_contract_for_headers(csv_headers, root)
        else:
            selector = args.contract_version
            cpath = contract_path(selector, root)
            contract = load_contract(cpath)
            if csv_headers != headers(contract):
                raise ValueError(f"CSV header does not match explicitly selected {selector} contract")
        row_results = [validate_csv_row(contract, csv_headers, row) for row in rows]
        any_errors = [e for result in row_results for e in result["errors"]]
        upload_ready = bool(rows) and all(result.get("elevenlabs_upload_ready", result["batch_ready"]) for result in row_results)
        production_gate = bool(rows) and all(result.get("production_prerequisite_gate_passed", result["outreach_policy_gate_passed"]) for result in row_results)
        if (args.require_batch_ready or args.require_elevenlabs_upload_ready) and not upload_ready:
            any_errors.append("elevenlabs_upload_ready_required")
        if args.require_production_prerequisites and not production_gate:
            any_errors.append("production_prerequisites_required")
        payload = {
            "status": "PASS" if not any_errors else "FAIL",
            "contract_selector": selector,
            "contract_version": contract.get("version"),
            "contract_sha256": sha256_file(cpath),
            "field_count": len(csv_headers),
            "utf8_bom": has_bom,
            "rows": row_results,
            "elevenlabs_upload_ready": upload_ready,
            "batch_ready": upload_ready,
            "production_prerequisite_gate_passed": production_gate,
            "outreach_policy_gate_passed": production_gate,
            "live_call_production_status": "NOT_ASSESSED",
            "errors": any_errors,
        }
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if any_errors:
            print("FAIL: " + "; ".join(any_errors), file=sys.stderr)
            return 1
        if rows:
            print(
                f"PASS: rows={len(rows)} fields={len(csv_headers)} contract={selector} "
                f"elevenlabs_upload_ready={str(upload_ready).lower()} production_prerequisite_gate={str(production_gate).lower()} "
                "live_call_production_status=not_assessed"
            )
        else:
            print(f"PASS: header-only template fields={len(csv_headers)} contract={selector}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
