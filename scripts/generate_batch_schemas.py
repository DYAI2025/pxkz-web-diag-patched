#!/usr/bin/env python3
"""Generate default v1.3 plus compatible v1.2/v1.1/legacy v1 batch schemas from bundled contracts."""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_contract import context_allowed_names, contract_path, has_classification_model, load_contract, sha256_file, specs_by_name  # noqa: E402


def json_type(contract_type: str):
    mapping = {"String": "string", "Boolean": "boolean", "Number": "number", "string": "string", "boolean": "boolean", "number": "number"}
    return mapping[contract_type]


def schemas_for(contract: dict, digest: str, label: str) -> tuple[dict, dict]:
    specs = specs_by_name(contract)
    allowed = context_allowed_names(contract)
    context_props = {name: {"type": json_type(str(specs[name]["type"]))} for name in allowed}
    context_props["_contract_digest"] = {"type": "string", "const": digest}
    context_props["_contract_version"] = {"type": "string", "const": str(contract.get("version"))}
    context_props["_allow_website_language_customer_language_default"] = {"type": "boolean"}
    context = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Pixelkiez ElevenLabs Batch Context {label}",
        "description": "Generated from the selected canonical batch contract. Audit-owned fields are intentionally excluded from batch_context.",
        "type": "object",
        "additionalProperties": False,
        "properties": context_props,
        "x-contract-version": str(contract.get("version")),
        "x-generated-from-contract-sha256": digest,
    }
    row_props = {}
    for name, spec in specs.items():
        prop = {
            "type": [json_type(str(spec["type"])), "null"],
            "x-requiredness": spec.get("required"),
            "x-source": spec.get("source"),
        }
        if has_classification_model(contract):
            prop["x-v1.3-classification"] = spec.get("classification")
        row_props[name] = prop
    row = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Pixelkiez ElevenLabs Batch Row {label}",
        "type": "object",
        "additionalProperties": False,
        "properties": row_props,
        "required": list(row_props),
        "x-contract-version": str(contract.get("version")),
        "x-generated-from-contract-sha256": digest,
        "x-csv-serialization": {"encoding": "utf-8-sig", "delimiter": ","},
    }
    if has_classification_model(contract):
        row["x-readiness-model"] = contract.get("classification_model")
        row["x-classification-counts"] = contract.get("classification_counts")
    return context, row


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: generate_batch_schemas.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    out = root / "schemas"; out.mkdir(parents=True, exist_ok=True)
    for selector, suffix in (("v1", ".v1"), ("v1.1", ".v1.1"), ("v1.2", ".v1.2"), ("v1.3", ".v1.3")):
        path = contract_path(selector, root)
        contract = load_contract(path)
        digest = sha256_file(path)
        context, row = schemas_for(contract, digest, selector)
        (out / f"batch-context{suffix}.schema.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"batch-row{suffix}.schema.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if selector == "v1.3":
            (out / "batch-context.schema.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (out / "batch-row.schema.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: generated batch schemas for v1, v1.1, v1.2 and v1.3; default schemas=v1.3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
