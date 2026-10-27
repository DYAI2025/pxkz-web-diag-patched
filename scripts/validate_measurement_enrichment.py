#!/usr/bin/env python3
"""Validate Pixelkiez measurement-enrichment schema and truth/security invariants."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEY_RE = re.compile(r"(?:token|password|passwd|secret|api[_-]?key|authorization|credential)", re.I)
SECRET_VALUE_RE = re.compile(r"^(?:Bearer|Basic)\s+[A-Za-z0-9+/=_\-.]+", re.I)
MEASURED = {"MEASURED", "OBSERVED"}


def fail(msg: str) -> int:
    print("FAIL: " + msg, file=sys.stderr)
    return 1


def scan_secrets(value: Any, path: str = "$", errors: list[str] | None = None) -> list[str]:
    errors = errors or []
    if isinstance(value, dict):
        for k, v in value.items():
            if SECRET_KEY_RE.search(str(k)):
                errors.append(f"secret-like key at {path}.{k}")
            scan_secrets(v, f"{path}.{k}", errors)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            scan_secrets(v, f"{path}[{i}]", errors)
    elif isinstance(value, str) and SECRET_VALUE_RE.search(value.strip()):
        errors.append(f"secret-like value at {path}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_measurement_enrichment.py <measurement-enrichment.json>")
    path = Path(argv[1])
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict) and "measurement_enrichment" in loaded:
            data = loaded.get("measurement_enrichment")
            if data is None:
                print("PASS: no measurement enrichment attached")
                return 0
        elif isinstance(loaded, dict) and "metrics" in loaded and "sources" in loaded and "target_url" in loaded:
            data = loaded
        elif isinstance(loaded, dict) and "meta" in loaded and "metrics" in loaded:
            print("PASS: no measurement enrichment attached")
            return 0
        else:
            data = loaded
        schema = json.loads((ROOT / "schemas/measurement-enrichment.schema.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "assets/enrichment-metric-registry.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(str(exc))
    errs = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    errors = [f"schema:{'.'.join(map(str,e.path))}:{e.message}" for e in errs]
    known = {str(x["id"]) for x in registry.get("metrics", [])}
    seen: set[tuple[str, str | None, str | None, str | None]] = set()
    for row in data.get("metrics", []):
        mid = str(row.get("id"))
        if mid not in known:
            errors.append(f"unknown metric {mid}")
        key = (mid, row.get("query"), row.get("device"), row.get("evidence_ref"))
        if key in seen:
            errors.append(f"duplicate metric record {key}")
        seen.add(key)
        status = str(row.get("status"))
        if status in MEASURED:
            if row.get("value") is None:
                errors.append(f"{mid} {status} requires value")
            if not row.get("observed_at"):
                errors.append(f"{mid} {status} requires observed_at")
        else:
            if row.get("value") is not None:
                errors.append(f"{mid} unavailable/not-assessed status must have null value")
            if row.get("measurement_class") != "not_assessed":
                errors.append(f"{mid} unavailable/not-assessed status must use measurement_class=not_assessed")
        if mid == "SERP_CURRENT_POSITION" and not row.get("query"):
            errors.append("SERP_CURRENT_POSITION requires query")
        if mid == "SERP_CURRENT_PAGE" and not row.get("query"):
            errors.append("SERP_CURRENT_PAGE requires query")
        if mid.startswith("GSC_") and row.get("source_provider") and "Search Console" in str(row.get("source_provider")) and mid in {"GSC_AVG_POSITION","GSC_IMPRESSIONS","GSC_CLICKS","GSC_CTR"} and not row.get("date_range"):
            errors.append(f"{mid} Search Console metric requires date_range")
        if mid.startswith("PSI_"):
            boundary = str(row.get("claim_boundary", "")).casefold()
            if not any(token in boundary for token in ("lab", "labor")) or not any(token in boundary for token in ("kein crux", "keine reale", "kein feldwert", "keine garantie für reale")):
                errors.append(f"{mid} must explicitly preserve lab-vs-field boundary")
        if mid == "GA4_PHONE_CLICKS" and "anruf" not in str(row.get("claim_boundary", "")).casefold():
            errors.append("GA4_PHONE_CLICKS boundary must reject call/lead equivalence")
        if mid.startswith("A11Y_") and not row.get("manual_review_required"):
            errors.append(f"{mid} must require manual accessibility review")
        if mid.startswith("PRIVACY_") or mid.startswith("CONSENT_"):
            if not row.get("legal_review_required"):
                errors.append(f"{mid} must preserve legal-review boundary")
    errors += scan_secrets(data)
    if errors:
        for e in errors[:50]:
            print("FAIL: " + e, file=sys.stderr)
        return 1
    print(f"PASS: measurement enrichment metrics={len(data.get('metrics', []))} sources={len(data.get('sources', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
