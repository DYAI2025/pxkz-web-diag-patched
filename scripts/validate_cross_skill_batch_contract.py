#!/usr/bin/env python3
"""Validate Website Diagnosis v1.3 against an actual Voice Architect or receipt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_contract import contract_path, headers, load_contract, sha256_file  # noqa: E402


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def resolve_other(path: Path, own_headers: list[str]) -> tuple[str | None, str | None, list[str] | None, str]:
    source = path
    if path.is_dir():
        source = path / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.3.json"
        if not source.is_file():
            raise ValueError(f"installed consumer v1.3 contract missing: {source}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("fields"), list):
        return sha256_file(source), str(data.get("version") or ""), [f.get("name") for f in data["fields"]], str(source)
    if isinstance(data, dict):
        binding = data.get("batch_contract") if isinstance(data.get("batch_contract"), dict) else data
        digest = binding.get("sha256") or data.get("contract_sha256")
        version = binding.get("version") or data.get("contract_version")
        other_headers = data.get("headers")
        if other_headers is None and binding.get("field_count") == len(own_headers):
            other_headers = own_headers
        return digest, str(version or ""), other_headers, str(source)
    raise ValueError("unsupported sibling evidence JSON")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_cross_skill_batch_contract.py <installed-consumer-dir|v1.3-contract|receipt.json>")
    root = Path(__file__).resolve().parents[1]
    own_path = contract_path("v1.3", root)
    own = load_contract(own_path)
    own_digest = sha256_file(own_path)
    own_headers = headers(own)
    try:
        other_digest, other_version, other_headers, source = resolve_other(Path(argv[1]).resolve(), own_headers)
    except Exception as exc:
        return fail(str(exc))
    if other_digest != own_digest:
        return fail(f"contract digest mismatch own={own_digest} consumer={other_digest} source={source}")
    if other_version != str(own.get("version")):
        return fail(f"contract version mismatch own={own.get('version')} consumer={other_version}")
    if other_headers != own_headers:
        return fail("v1.3 header/name/case/order parity mismatch")
    print(f"PASS: installed consumer parity {len(own_headers)}/{len(own_headers)} version={other_version} digest={own_digest} source={source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
