#!/usr/bin/env python3
"""Deterministic utilities for Pixelkiez ElevenLabs batch contracts v1 through v1.3."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SKILL_DIR = Path(__file__).resolve().parent.parent
LEGACY_V1_PATH = SKILL_DIR / "contracts" / "pixelkiez_elevenlabs_batch_variable_contract.v1.json"
CONTRACT_V11_PATH = SKILL_DIR / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.1.json"
CONTRACT_V12_PATH = SKILL_DIR / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.2.json"
CONTRACT_V13_PATH = SKILL_DIR / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.3.json"
DEFAULT_CONTRACT_VERSION = "v1.3"
# Backward import compatibility: callers importing CONTRACT_PATH now get the default new-export contract.
CONTRACT_PATH = CONTRACT_V13_PATH
MANIFEST_PATH = SKILL_DIR / "contracts" / "contract-manifest.json"
E164_RE = re.compile(r"^\+[1-9][0-9]{7,14}$")
AUDIT_OWNED_SOURCE_MARKERS = ("validated audit packet", "compiler output")
SPECIAL_CONTEXT_KEYS = {"_contract_digest", "_contract_version", "_allow_website_language_customer_language_default"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_path(version: str = DEFAULT_CONTRACT_VERSION, root: Path | None = None) -> Path:
    base = root or SKILL_DIR
    if version == "v1":
        return base / "contracts" / LEGACY_V1_PATH.name
    if version in {"v1.1", "1.1", "1.1.0"}:
        return base / "contracts" / CONTRACT_V11_PATH.name
    if version in {"v1.2", "1.2", "1.2.0"}:
        return base / "contracts" / CONTRACT_V12_PATH.name
    if version in {"v1.3", "1.3", "1.3.0"}:
        return base / "contracts" / CONTRACT_V13_PATH.name
    raise ValueError(f"unsupported contract version selector: {version}")


def load_contract(path: Path | None = None, version: str | None = None) -> dict[str, Any]:
    p = path or contract_path(version or DEFAULT_CONTRACT_VERSION)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid batch contract")
    if not isinstance(data.get("variables"), list) and not isinstance(data.get("fields"), list):
        raise ValueError("invalid batch contract: variables/fields missing")
    return data


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or MANIFEST_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid contract manifest")
    return data


def _type_for_website(value: str) -> str:
    mapping = {"string": "String", "boolean": "Boolean", "number": "Number", "String": "String", "Boolean": "Boolean", "Number": "Number"}
    if value not in mapping:
        raise ValueError(f"unsupported contract type {value!r}")
    return mapping[value]


def variable_specs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize legacy Website v1 and shared canonical v1.1/v1.2/v1.3 field metadata."""
    if isinstance(contract.get("variables"), list):
        specs = [dict(v) for v in contract["variables"]]
    else:
        specs = []
        for field in contract.get("fields", []):
            if not isinstance(field, dict):
                raise ValueError("contract fields malformed")
            specs.append({
                **field,
                "required": field.get("requiredness"),
                "type": _type_for_website(str(field.get("type"))),
                "source": field.get("source") or field.get("authority", ""),
                "placeholder": field.get("placeholder") or field.get("prompt_placeholder", ""),
                "example": field.get("example", ""),
                "notes": field.get("notes", ""),
            })
    if not all(isinstance(v, dict) and isinstance(v.get("name"), str) for v in specs):
        raise ValueError("contract variables malformed")
    names = [v["name"] for v in specs]
    if len(names) != len(set(names)):
        raise ValueError("duplicate contract variable names")
    return specs


def headers(contract: dict[str, Any]) -> list[str]:
    return [v["name"] for v in variable_specs(contract)]


def specs_by_name(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {v["name"]: v for v in variable_specs(contract)}


def required_names(contract: dict[str, Any]) -> list[str]:
    return [v["name"] for v in variable_specs(contract) if v.get("required") in {"YES", "YES*"}]


def recommended_names(contract: dict[str, Any]) -> list[str]:
    return [v["name"] for v in variable_specs(contract) if v.get("required") == "RECOMMENDED"]


V13_CLASSIFICATIONS = {"INTERNAL_RECORD", "EL_RUNTIME_REQUIRED", "EL_RUNTIME_DEFAULTED", "OPTIONAL", "PRODUCTION_GATE_ONLY"}


def has_classification_model(contract: dict[str, Any]) -> bool:
    return str(contract.get("classification_model", "")).startswith("v1.3-")


def classification_names(contract: dict[str, Any], classification: str) -> list[str]:
    if classification not in V13_CLASSIFICATIONS:
        raise ValueError(f"unknown v1.3 classification: {classification}")
    return [v["name"] for v in variable_specs(contract) if v.get("classification") == classification]


def runtime_required_names(contract: dict[str, Any]) -> list[str]:
    return classification_names(contract, "EL_RUNTIME_REQUIRED") if has_classification_model(contract) else required_names(contract)


def runtime_defaulted_names(contract: dict[str, Any]) -> list[str]:
    return classification_names(contract, "EL_RUNTIME_DEFAULTED") if has_classification_model(contract) else []


def production_gate_names(contract: dict[str, Any]) -> list[str]:
    return classification_names(contract, "PRODUCTION_GATE_ONLY") if has_classification_model(contract) else []


def optional_names(contract: dict[str, Any]) -> list[str]:
    return classification_names(contract, "OPTIONAL") if has_classification_model(contract) else []


def internal_record_names(contract: dict[str, Any]) -> list[str]:
    return classification_names(contract, "INTERNAL_RECORD") if has_classification_model(contract) else []


def classification_counts(contract: dict[str, Any]) -> dict[str, int]:
    if not has_classification_model(contract):
        return {}
    return {name: len(classification_names(contract, name)) for name in ("INTERNAL_RECORD", "EL_RUNTIME_REQUIRED", "EL_RUNTIME_DEFAULTED", "OPTIONAL", "PRODUCTION_GATE_ONLY")}


def requiredness_counts(contract: dict[str, Any]) -> dict[str, int]:
    counts = Counter(str(v.get("required")) for v in variable_specs(contract))
    return {k: counts.get(k, 0) for k in ("YES", "YES*", "RECOMMENDED", "OPTIONAL")}


def canonical_contract_version(contract: dict[str, Any]) -> str:
    return str(contract.get("version", ""))


def is_audit_owned(spec: dict[str, Any]) -> bool:
    source = str(spec.get("source", "")).lower()
    return any(marker in source for marker in AUDIT_OWNED_SOURCE_MARKERS)


def context_allowed_names(contract: dict[str, Any]) -> list[str]:
    return [v["name"] for v in variable_specs(contract) if not is_audit_owned(v)]


def normalize_scalar(value: Any, type_name: str) -> Any:
    if value is None or value == "":
        return None
    type_name = _type_for_website(type_name)
    if type_name == "String":
        if not isinstance(value, str):
            raise ValueError("expected String")
        return value
    if type_name == "Boolean":
        if not isinstance(value, bool):
            raise ValueError("expected Boolean")
        return value
    if type_name == "Number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("expected Number")
        return value
    raise ValueError(f"unsupported contract type {type_name!r}")


def serialize_value(value: Any, type_name: str) -> str:
    if value is None or value == "":
        return ""
    type_name = _type_for_website(type_name)
    if type_name == "Boolean":
        if not isinstance(value, bool):
            raise ValueError("Boolean values must be native booleans before serialization")
        return "true" if value else "false"
    if type_name == "Number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Number values must be numeric before serialization")
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return format(value, ".15g")
    if type_name == "String":
        if not isinstance(value, str):
            raise ValueError("String values must be strings before serialization")
        return value
    raise ValueError(f"unsupported type {type_name}")


def parse_csv(path: Path) -> tuple[list[str], list[list[str]], bool]:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return [], [], has_bom
    return rows[0], rows[1:], has_bom


def _col_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def read_xlsx_sheet(path: Path, sheet_name: str) -> list[list[str | None]]:
    """Read simple XLSX sheet values with only the Python standard library."""
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall(f"{{{ns_pkg}}}Relationship")}
        target = None
        for sheet in wb.findall(f".//{{{ns_main}}}sheet"):
            if sheet.attrib.get("name") == sheet_name:
                rid = sheet.attrib.get(f"{{{ns_rel}}}id")
                target = relmap.get(rid or "")
                break
        if target is None:
            raise ValueError(f"sheet not found: {sheet_name}")
        sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target.lstrip("/")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{{{ns_main}}}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns_main}}}t")))
        sheet_root = ET.fromstring(zf.read(sheet_path))
        out: list[list[str | None]] = []
        for row_el in sheet_root.findall(f".//{{{ns_main}}}sheetData/{{{ns_main}}}row"):
            cells: dict[int, str | None] = {}
            for cell in row_el.findall(f"{{{ns_main}}}c"):
                idx = _col_index(cell.attrib.get("r", "A1"))
                typ = cell.attrib.get("t")
                if typ == "inlineStr":
                    val = "".join(t.text or "" for t in cell.iter(f"{{{ns_main}}}t"))
                else:
                    v = cell.find(f"{{{ns_main}}}v")
                    raw = v.text if v is not None else None
                    if raw is None:
                        val = None
                    elif typ == "s":
                        val = shared[int(raw)]
                    elif typ == "b":
                        val = "true" if raw == "1" else "false"
                    else:
                        val = raw
                cells[idx] = val
            width = (max(cells) + 1) if cells else 0
            row = [None] * width
            for idx, val in cells.items():
                row[idx] = val
            out.append(row)
        return out



def detect_contract_for_headers(csv_headers: list[str], root: Path | None = None) -> tuple[str, Path, dict[str, Any]]:
    base = root or SKILL_DIR
    matches: list[tuple[str, Path, dict[str, Any]]] = []
    for selector in ("v1", "v1.1", "v1.2", "v1.3"):
        p = contract_path(selector, base)
        contract = load_contract(p)
        if csv_headers == headers(contract):
            matches.append((selector, p, contract))
    if not matches:
        raise ValueError(f"CSV headers do not exactly match a supported contract version; supported field counts are 82, 83 and 96, got {len(csv_headers)}")
    if len(matches) == 1:
        return matches[0]
    # v1.2 and v1.3 intentionally share the same 96-column wire header. Auto mode resolves
    # that shape to the latest default semantics; legacy v1.2 remains explicitly selectable.
    for item in matches:
        if item[0] == DEFAULT_CONTRACT_VERSION:
            return item
    raise ValueError("CSV header matches multiple contract versions; select --contract-version explicitly")


def validate_csv_row(contract: dict[str, Any], csv_headers: list[str], row: list[str]) -> dict[str, Any]:
    expected = headers(contract)
    errors: list[str] = []
    classified = has_classification_model(contract)
    if csv_headers != expected:
        missing = [h for h in expected if h not in csv_headers]
        extra = [h for h in csv_headers if h not in expected]
        errors.append(f"header_mismatch:missing={missing}:extra={extra}")
        return {
            "errors": errors,
            "missing_required_fields": (runtime_required_names(contract) + runtime_defaulted_names(contract)) if classified else required_names(contract),
            "missing_recommended_fields": [] if classified else recommended_names(contract),
            "missing_runtime_required_fields": runtime_required_names(contract) if classified else [],
            "missing_runtime_defaulted_fields": runtime_defaulted_names(contract) if classified else [],
            "missing_production_gate_fields": production_gate_names(contract) if classified else [],
            "optional_blank_fields": optional_names(contract) if classified else [],
            "internal_blank_fields": internal_record_names(contract) if classified else [],
            "elevenlabs_upload_ready": False,
            "batch_ready": False,
            "production_prerequisite_gate_passed": False,
            "outreach_policy_gate_passed": False,
        }
    if len(row) != len(expected):
        errors.append(f"row_length:{len(row)}!={len(expected)}")
        row = row[: len(expected)] + [""] * max(0, len(expected) - len(row))
    values = dict(zip(expected, row))
    specs = specs_by_name(contract)
    for name, value in values.items():
        if value == "":
            continue
        if value.strip().lower() == "null":
            errors.append(f"literal_null_forbidden:{name}")
            continue
        typ = specs[name].get("type")
        if typ == "Boolean" and value not in {"true", "false"}:
            errors.append(f"invalid_boolean:{name}")
        elif typ == "Number":
            try:
                float(value)
            except Exception:
                errors.append(f"invalid_number:{name}")
    for name in ("phone_number", "recipient_number"):
        value = values.get(name, "")
        if value and not E164_RE.fullmatch(value):
            errors.append(f"invalid_e164:{name}")
    phone = values.get("phone_number", "")
    recipient = values.get("recipient_number", "")
    if phone and recipient and phone != recipient:
        errors.append("recipient_number_mirror_mismatch")
    if bool(phone) != bool(recipient):
        errors.append("phone_recipient_pair_incomplete")
    for idx in (1, 2, 3):
        cls = values.get(f"audit_hook_{idx}_evidence_class", "")
        spoken = values.get(f"audit_hook_{idx}_spoken", "")
        if cls == "UNKNOWN" and spoken:
            errors.append(f"unknown_hook_must_not_be_spoken:{idx}")

    compliance = values.get("compliance_status", "")
    dnc = values.get("do_not_contact", "")
    recording = values.get("recording_status", "")

    if classified:
        missing_runtime_required = [n for n in runtime_required_names(contract) if values.get(n, "") == ""]
        missing_runtime_defaulted = [n for n in runtime_defaulted_names(contract) if values.get(n, "") == ""]
        missing_production = [n for n in production_gate_names(contract) if values.get(n, "") == ""]
        optional_blank = [n for n in optional_names(contract) if values.get(n, "") == ""]
        internal_blank = [n for n in internal_record_names(contract) if values.get(n, "") == ""]
        upload_ready = not errors and not missing_runtime_required and not missing_runtime_defaulted
        production_gate_passed = bool(
            upload_ready and not missing_production and compliance == "APPROVED" and dnc == "false" and recording in {"OFF", "APPROVED"}
        )
        return {
            "errors": errors,
            "missing_required_fields": missing_runtime_required + missing_runtime_defaulted,
            "missing_recommended_fields": [],
            "missing_runtime_required_fields": missing_runtime_required,
            "missing_runtime_defaulted_fields": missing_runtime_defaulted,
            "missing_production_gate_fields": missing_production,
            "optional_blank_fields": optional_blank,
            "internal_blank_fields": internal_blank,
            "elevenlabs_upload_ready": upload_ready,
            "batch_ready": upload_ready,
            "production_prerequisite_gate_passed": production_gate_passed,
            "outreach_policy_gate_passed": production_gate_passed,
        }

    missing_required = [n for n in required_names(contract) if values.get(n, "") == ""]
    missing_recommended = [n for n in recommended_names(contract) if values.get(n, "") == ""]
    batch_ready = not errors and not missing_required
    policy_gate_passed = bool(batch_ready and compliance == "APPROVED" and dnc == "false" and recording in {"OFF", "APPROVED"})
    return {
        "errors": errors,
        "missing_required_fields": missing_required,
        "missing_recommended_fields": missing_recommended,
        "missing_runtime_required_fields": [],
        "missing_runtime_defaulted_fields": [],
        "missing_production_gate_fields": [],
        "optional_blank_fields": [],
        "internal_blank_fields": [],
        "elevenlabs_upload_ready": batch_ready,
        "batch_ready": batch_ready,
        "production_prerequisite_gate_passed": policy_gate_passed,
        "outreach_policy_gate_passed": policy_gate_passed,
    }
