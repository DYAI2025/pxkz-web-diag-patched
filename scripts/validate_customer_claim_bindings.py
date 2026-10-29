#!/usr/bin/env python3
"""Fail-closed check that every customer strength is bound to scored metrics that read "Klar".

Usage: validate_customer_claim_bindings.py <diagnosis-report.json> <client-report-model.json> <customer-claim-bindings.json>

The sidecar is written by build_client_report_model.py --claim-bindings-out. This validator does not trust
the sidecar's own admitted flags: it re-derives every admitted claim against the scored report, binds the
sidecar to both digests and to the audited URL, and requires that the rendered strengths equal the admitted set.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from customer_status import customer_status  # noqa: E402
from legal_customer_projection import contested_identity_surface, contested_legal_surface  # noqa: E402

UNASSESSED_CLASSES = {None, "", "not_assessed", "inferred_risk"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def errors_for(scored_path: Path, model_path: Path, bindings_path: Path) -> list[str]:
    scored = json.loads(scored_path.read_text(encoding="utf-8"))
    model = json.loads(model_path.read_text(encoding="utf-8"))
    bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if bindings.get("scored_report_sha256") != sha(scored_path):
        errors.append("SCORED_DIGEST_MISMATCH")
    if bindings.get("client_model_sha256") != sha(model_path):
        errors.append("MODEL_DIGEST_MISMATCH")
    if bindings.get("audited_url") != str((scored.get("meta") or {}).get("audited_url") or ""):
        errors.append("AUDITED_URL_MISMATCH")
    metrics = {str(m.get("id")): m for m in scored.get("metrics", []) if isinstance(m, dict)}
    findings = {str(f.get("id")): f for f in scored.get("findings", []) if isinstance(f, dict)}
    contested = set(contested_legal_surface(scored)) | set(contested_identity_surface(scored))
    claims = [c for c in bindings.get("claims", []) if isinstance(c, dict)]
    admitted = [c for c in claims if c.get("admitted") is True]
    rendered = list((model.get("executive") or {}).get("strengths", []))
    if sorted(str(c.get("text")) for c in admitted) != sorted(rendered):
        errors.append("RENDERED_STRENGTHS_DIFFER_FROM_ADMITTED_CLAIMS")
    for c in admitted:
        ref_id = str(c.get("finding_ref"))
        finding = findings.get(ref_id)
        if finding is None or finding.get("severity") != "positive":
            errors.append(f"ADMITTED_WITHOUT_POSITIVE_FINDING:{ref_id}")
            continue
        refs = [str(x) for x in c.get("metric_refs", [])]
        if not refs or refs != [str(x) for x in finding.get("metric_refs", [])]:
            errors.append(f"METRIC_REFS_NOT_FROM_FINDING:{ref_id}")
        for ref in refs:
            m = metrics.get(ref)
            if m is None or m.get("measurement_class") in UNASSESSED_CLASSES:
                errors.append(f"REF_NOT_ASSESSED:{ref_id}:{ref}")
            elif customer_status(m)["key"] != "CLEAR":
                errors.append(f"REF_NOT_CLEAR:{ref_id}:{ref}")
            if ref in contested:
                errors.append(f"REF_CONTESTED:{ref_id}:{ref}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        errors = errors_for(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    except Exception as exc:  # unreadable or malformed input fails closed
        errors = [f"UNREADABLE_INPUT:{type(exc).__name__}:{exc}"]
    for error in errors:
        print(f"CLAIM_BINDING_FAIL: {error}")
    print("PASS: customer claim bindings consistent" if not errors else f"FAIL: {len(errors)} claim binding error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
