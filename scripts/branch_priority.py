#!/usr/bin/env python3
"""Evidence-bounded, non-scoring industry priorities for customer lever selection.

No built-in industry weights exist. This module only applies validated, approved
profiles when an explicit, sourced context selects one. Otherwise the legacy
selector remains authoritative and unchanged.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "branch-priority.schema.json"
DEFAULT_PROFILES = ROOT / "assets" / "branch-priority-profiles.v1.json"
CATEGORIES = (
    "findability_seo", "performance_technology", "ux_conversion",
    "accessibility", "trust_privacy_content", "ai_readiness",
)
ROLES = {"BUSINESS_GAP", "PREMIUM_OPPORTUNITY", "PRECISION_DEMONSTRATION"}
SYNTHETIC_RX = re.compile(r"SYNTHETIC|TEST[ _]DATA|FIXTURE", re.I)


class BranchPriorityError(ValueError):
    """Unsupported or contradictory contextual priority evidence."""


def load_json(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise BranchPriorityError(f"expected JSON object at {path}")
    return result


def validate_structured(context: dict[str, Any], catalog: dict[str, Any]) -> None:
    schema = load_json(SCHEMA)
    for field, value in (("context", context), ("catalog", catalog)):
        validator_schema = {**schema, "$ref": f"#/$defs/{field}"}
        errors = sorted(Draft202012Validator(validator_schema).iter_errors(value), key=lambda e: str(e.path))
        if errors:
            e = errors[0]
            raise BranchPriorityError(f"{field}: {'.'.join(map(str, e.path))}: {e.message}")
    for date_value in [context["audit_date"], *[v for p in catalog["profiles"] for v in (p["effective_from"], p["effective_until"])]]:
        try:
            dt.date.fromisoformat(date_value)
        except ValueError as exc:
            raise BranchPriorityError("invalid ISO date") from exc
    if (catalog["status"] == "NO_APPROVED_PROFILES_REGISTERED") != (len(catalog["profiles"]) == 0):
        raise BranchPriorityError("catalog status does not match profile contents")
    ids: set[str] = set()
    for p in catalog["profiles"]:
        if p["effective_from"] > p["effective_until"]:
            raise BranchPriorityError("profile dates reversed")
        if p["profile_id"] in ids:
            raise BranchPriorityError("duplicate approved profile_id")
        ids.add(p["profile_id"])
        for weights in [p["category_weights"], *p.get("goal_weights", {}).values()]:
            if set(weights) != set(CATEGORIES) or sum(weights.values()) != 100:
                raise BranchPriorityError("each priority weight map must cover six categories and sum to 100")


def choose_priority(
    report: dict[str, Any],
    context: dict[str, Any] | None,
    catalog: dict[str, Any] | None,
) -> tuple[dict[str, int] | None, dict[str, Any]]:
    """Return optional weights + explicit provenance, never a website quality score."""
    decision: dict[str, Any] = {
        "mode": "LEGACY_PRIORITY", "reason": "NO_CONTEXT", "profile_id": None,
        "goal_override_used": False, "score_changed": False,
        "benchmark_comparison_authorized": False,
    }
    if context is None:
        return None, decision
    if catalog is None:
        catalog = load_json(DEFAULT_PROFILES)
    validate_structured(context, catalog)

    # A declared industry identity is not proof. Match its source exactly to
    # available first-party audit evidence or require the explicit owner source.
    ident = context["identity"]
    if ident["evidence_kind"] == "FIRST_PARTY_PUBLIC":
        first_party_source = next((
            e for e in report.get("sources", [])
            if isinstance(e, dict) and str(e.get("id")) == ident["evidence_ref"]
        ), None)
        audited = urlsplit(str(report.get("meta", {}).get("audited_url", "")))
        location = urlsplit(str((first_party_source or {}).get("location", "")))
        if not (
            first_party_source and first_party_source.get("type") == "primary"
            and audited.scheme in {"http", "https"} and location.scheme in {"http", "https"}
            and audited.hostname and audited.hostname == location.hostname
        ):
            raise BranchPriorityError("industry identity source must be an inspected first-party URL on the audited host")

    matches = [
        p for p in catalog["profiles"]
        if p["industry_id"] == context["industry_id"]
        and p["business_model_id"] == context["business_model_id"]
        and p["status"] == "APPROVED"
        and p["effective_from"] <= context["audit_date"] <= p["effective_until"]
    ]
    if not matches:
        decision["reason"] = "NO_APPROVED_APPLICABLE_PROFILE"
        return None, decision
    if len(matches) != 1:
        raise BranchPriorityError("ambiguous approved industry profile applicability")
    profile = matches[0]
    weights = profile["category_weights"]
    decision.update({
        "mode": "APPROVED_INDUSTRY_PROFILE",
        "reason": "APPROVED_PROFILE_AND_MATCHING_EVIDENCE_CONTEXT",
        "profile_id": profile["profile_id"],
        "profile_source_ref": profile["source_ref"],
        "profile_basis": profile["basis"],
        "identity_evidence_ref": ident["evidence_ref"],
    })

    goal = context.get("goal")
    if goal and goal["source"] == "OWNER_CONFIRMED":
        goal_weights = profile.get("goal_weights", {}).get(goal["goal_id"])
        if goal_weights is not None:
            weights = goal_weights
            decision["mode"] = "APPROVED_OWNER_GOAL_PROFILE"
            decision["goal_override_used"] = True
            decision["goal_id"] = goal["goal_id"]
            decision["goal_evidence_ref"] = goal["evidence_ref"]
        else:
            decision["goal_override_reason"] = "NO_APPROVED_GOAL_WEIGHTS"
    return weights, decision


def validated_roles(report: dict[str, Any], context: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Role markers are eligible only with exact finding/evidence matches."""
    if context is None:
        return {}
    findings = {str(f.get("id")): f for f in report.get("findings", []) if isinstance(f, dict)}
    roles = {}
    for item in context.get("roles", []):
        fid = item["finding_id"]
        if fid in roles:
            raise BranchPriorityError("duplicate finding role")
        f = findings.get(fid)
        if f is None:
            raise BranchPriorityError(f"role finding not present: {fid}")
        available = {
            str(e.get("id")) for e in f.get("evidence", [])
            if isinstance(e, dict) and e.get("id")
        }
        if not set(item["evidence_refs"]) <= available:
            raise BranchPriorityError(f"role evidence mismatch: {fid}")
        roles[fid] = item
    return roles


def preferred_order(
    findings: list[dict[str, Any]], weights: dict[str, int],
    roles: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort within established severity and confidence bands, then by weights.

    This is ranking for *customer-story selection*, NOT quality scoring.
    Weights and roles only order genuine ties (same severity, same
    confidence); they never override the existing evidence/confidence gate.
    Do not replace mandatory/legal admission, criticality, or customer gates.
    """
    severity = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}
    role_order = {"PREMIUM_OPPORTUNITY": 0, "PRECISION_DEMONSTRATION": 1, "BUSINESS_GAP": 2}

    def key(f: dict[str, Any]) -> tuple[Any, ...]:
        fid = str(f.get("id", ""))
        role = roles.get(fid, {}).get("role", "BUSINESS_GAP")
        return (
            severity.get(str(f.get("severity")), 9),
            -int(f.get("confidence", 0)),
            -weights.get(str(f.get("category")), 0),
            role_order.get(role, 2),
            fid,
        )

    return sorted(findings, key=key)


def is_synthetic(catalog: dict[str, Any], profile_id: str | None) -> bool:
    profile = next((p for p in catalog.get("profiles", []) if p.get("profile_id") == profile_id), {})
    surface = " ".join(str(x) for x in (catalog.get("purpose"), profile.get("source_ref"), profile.get("basis"), profile.get("approved_by")))
    return bool(SYNTHETIC_RX.search(surface))


def resolve_priority(
    report: dict[str, Any],
    context: dict[str, Any] | None,
    catalog: dict[str, Any] | None,
    *,
    allow_synthetic: bool = False,
) -> tuple[dict[str, int] | None, dict[str, dict[str, Any]], dict[str, Any]]:
    """Fail-neutral wrapper: unusable context/profiles fall back to legacy order.

    Unsuitable, synthetic, contradictory, expired or unverified weights are
    ignored and recorded as uncertainty instead of changing the selection.
    """
    legacy = {
        "mode": "LEGACY_PRIORITY", "reason": "NO_CONTEXT", "profile_id": None,
        "goal_override_used": False, "score_changed": False,
        "benchmark_comparison_authorized": False, "uncertainty": [],
    }
    if context is None:
        return None, {}, legacy
    try:
        weights, decision = choose_priority(report, context, catalog)
    except BranchPriorityError as exc:
        return None, {}, {**legacy, "reason": "PROFILE_IGNORED", "uncertainty": [f"PRIORITY_CONTEXT_REJECTED: {exc}"]}
    decision.setdefault("uncertainty", [])
    if weights is None:
        # Roles only order ties under an applicable profile; without one they are inert.
        if context.get("roles"):
            decision["uncertainty"].append("ROLES_IGNORED_WITHOUT_APPLICABLE_PROFILE")
        return None, {}, decision
    synthetic = is_synthetic(catalog or load_json(DEFAULT_PROFILES), decision.get("profile_id"))
    decision["synthetic_test_profile"] = synthetic
    if synthetic and not allow_synthetic:
        return None, {}, {**legacy, "reason": "PROFILE_IGNORED", "profile_id": None, "synthetic_test_profile": True,
                          "uncertainty": [f"SYNTHETIC_PROFILE_NOT_FOR_CUSTOMER_USE: {decision.get('profile_id')}"]}
    try:
        roles = validated_roles(report, context)
    except BranchPriorityError as exc:
        return None, {}, {**legacy, "reason": "PROFILE_IGNORED", "uncertainty": [f"ROLE_EVIDENCE_REJECTED: {exc}"]}
    return weights, roles, decision


def selection_provenance(
    report: dict[str, Any],
    selected: list[dict[str, Any]],
    weights: dict[str, int] | None,
    roles: dict[str, dict[str, Any]],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Internal-only record of every deviation from the legacy customer selection."""
    from client_story import select_client_levers  # local import: client_story imports this module

    legacy_ids = [str(f.get("id")) for f in select_client_levers(report)]
    selected_ids = [str(f.get("id")) for f in selected]
    deviations = []
    for rank, f in enumerate(selected, 1):
        fid = str(f.get("id"))
        legacy_rank = legacy_ids.index(fid) + 1 if fid in legacy_ids else None
        if legacy_rank == rank:
            continue
        deviations.append({
            "finding_id": fid, "legacy_rank": legacy_rank, "selected_rank": rank,
            "severity": f.get("severity"), "confidence": f.get("confidence"), "category": f.get("category"),
            "category_weight": (weights or {}).get(str(f.get("category"))),
            "role": roles.get(fid, {}).get("role"),
            "reason": "APPROVED_PROFILE_GENUINE_TIE_ORDER",
            "profile_id": decision.get("profile_id"),
        })
    return {
        **decision,
        "legacy_selected_ids": legacy_ids,
        "selected_lever_ids": selected_ids,
        "displaced_legacy_ids": [x for x in legacy_ids if x not in selected_ids],
        "deviations": deviations,
        "candidate_role_ids": sorted(roles),
        "customer_pdf_contains_priority_metadata": False,
        "canonical_core_score_unchanged": True,
    }


def load_priority_inputs(
    context_path: str | None, catalog_path: str | None, catalog_sha256: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Shared CLI loading: an external catalog is trusted only with its exact SHA-256."""
    context = load_json(Path(context_path)) if context_path else None
    if catalog_path:
        candidate = Path(catalog_path)
        observed = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if not catalog_sha256 or observed != catalog_sha256.lower():
            raise BranchPriorityError("external industry catalog requires matching --priority-catalog-sha256")
        return context, load_json(candidate)
    if catalog_sha256:
        raise BranchPriorityError("priority catalog digest supplied without catalog")
    return context, None


def add_priority_arguments(parser: Any) -> None:
    parser.add_argument("--priority-context", help="Optional sourced sector/business-model context JSON")
    parser.add_argument("--priority-catalog", help="Optional approved industry weights catalog; no default estimates")
    parser.add_argument("--priority-catalog-sha256", help="Required exact SHA-256 for any external priority catalog")
    parser.add_argument("--priority-allow-synthetic", action="store_true",
                        help="Test mode only: honor profiles marked as synthetic test data")
