#!/usr/bin/env python3
"""Resolve validated Impressum sidecar evidence into one customer-risk decision.

This module never decides legal liability. It only decides whether a supported
provider-identification risk must be surfaced to the customer and at what
customer priority. Core score inputs are out of scope.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VALID_STATES = {"ASSESSED_DEFECT", "POSSIBLE_LEGAL_REVIEW", "CONFLICT"}
MANDATORY = {"MANDATORY_CRITICAL", "MANDATORY_HIGH"}
IDENTITY_METRICS = {"LEGAL-IMP-01", "LEGAL-IMP-02", "LEGAL-IMP-03"}
# Core metrics whose customer label covers the legal surface. TRUST-01 is presence-only, so a validated
# legal customer risk does not contradict its score, but it does contradict a customer-facing "Klar".
LEGAL_SURFACE_CORE_METRICS = frozenset({"TRUST-01"})


# Core metrics whose customer label speaks about who operates the site. While a provider-identity risk is
# projected they must not read as clear (their scores are untouched).
IDENTITY_SURFACE_CORE_METRICS = frozenset({"TRUST-04", "TRUST-07", "AI-01", "AI-06"})


def contested_identity_surface(report: dict[str, Any]) -> frozenset[str]:
    """Identity-related core metrics that cannot read as clear while a PROVIDER_IDENTITY risk is projected."""
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    if any(isinstance(f, dict) and isinstance(f.get("customer_risk"), dict)
           and f["customer_risk"].get("group") == "PROVIDER_IDENTITY" for f in findings):
        return IDENTITY_SURFACE_CORE_METRICS
    return frozenset()


def contested_legal_surface(report: dict[str, Any]) -> frozenset[str]:
    """Core metric ids whose customer status must not read as clear while a legal customer risk is projected.

    Findings carry customer_risk only as the validated projection of a supplied sidecar
    (build_audit_deliverables enforces LEGAL_SIDECAR_REQUIRED). Scores are untouched.
    """
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    if any(isinstance(f, dict) and isinstance(f.get("customer_risk"), dict) and f["customer_risk"] for f in findings):
        return LEGAL_SURFACE_CORE_METRICS
    return frozenset()


def _active_results(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        r for r in sidecar.get("results", [])
        if isinstance(r, dict)
        and r.get("result_state") in VALID_STATES
        and str(r.get("metric_id", "")).startswith("LEGAL-IMP-")
    ]


def _identity_related(result: dict[str, Any]) -> bool:
    mid = str(result.get("metric_id", ""))
    if mid in IDENTITY_METRICS:
        return True
    return result.get("base_dimension") in {"identity", "geographic_address"}


def resolve_projection(sidecar: dict[str, Any]) -> dict[str, Any]:
    results = _active_results(sidecar)
    overrides = sidecar.get("overrides") if isinstance(sidecar.get("overrides"), dict) else {}
    legal_refs = list(dict.fromkeys(str(r.get("metric_id")) for r in results if r.get("metric_id")))
    identity_related = [r for r in results if _identity_related(r)]

    if not results:
        return {
            "schema_version": "1.0",
            "required": False,
            "priority": "INTERNAL_ONLY",
            "claim_state": "NOT_ASSESSED",
            "group": "NONE",
            "legal_metric_refs": [],
            "warning_label": "",
            "reason": "NO_CUSTOMER_RELEVANT_LEGAL_RESULT",
        }

    any_assessed_critical = any(
        r.get("result_state") == "ASSESSED_DEFECT" and r.get("severity") == "critical"
        for r in results
    )
    any_assessed_high = any(
        r.get("result_state") == "ASSESSED_DEFECT" and r.get("severity") == "high"
        for r in results
    )
    identity_conflict = any(r.get("result_state") == "CONFLICT" for r in identity_related)

    if overrides.get("iles_critical_override") is True:
        priority = "MANDATORY_CRITICAL"
        reason = "ILES_CRITICAL_OVERRIDE"
    elif overrides.get("audit_priority_critical") is True:
        priority = "MANDATORY_CRITICAL"
        reason = "AUDIT_PRIORITY_CRITICAL"
    elif any_assessed_critical:
        priority = "MANDATORY_CRITICAL"
        reason = "ASSESSED_CRITICAL_DEFECT"
    elif identity_conflict:
        priority = "MANDATORY_HIGH"
        reason = "PROVIDER_IDENTITY_CONFLICT"
    elif any_assessed_high:
        priority = "MANDATORY_HIGH"
        reason = "ASSESSED_HIGH_DEFECT"
    else:
        priority = "ELIGIBLE"
        reason = "SUPPORTED_LEGAL_REVIEW_SIGNAL"

    if any(r.get("result_state") == "ASSESSED_DEFECT" for r in results):
        claim_state = "ASSESSED_DEFECT"
    elif any(r.get("result_state") == "CONFLICT" for r in results):
        claim_state = "CONFLICT"
    else:
        claim_state = "POSSIBLE_LEGAL_REVIEW"

    group = "PROVIDER_IDENTITY" if identity_related else "PROVIDER_INFORMATION"
    warning = (
        "Dringender rechtlicher Pr\u00fcfbedarf"
        if priority in MANDATORY
        else "Rechtlicher Pr\u00fcfhinweis"
    )
    return {
        "schema_version": "1.0",
        "required": priority in MANDATORY,
        "priority": priority,
        "claim_state": claim_state,
        "group": group,
        "legal_metric_refs": legal_refs,
        "warning_label": warning,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sidecar")
    parser.add_argument("output")
    args = parser.parse_args()
    sidecar = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    out = resolve_projection(sidecar)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: legal customer projection priority={out['priority']} required={out['required']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
