#!/usr/bin/env python3
"""Evidence-bounded, non-scoring industry priorities for customer lever selection.

No built-in industry weights exist. This module only applies validated, approved
profiles when an explicit, sourced context selects one. Otherwise the legacy
selector remains authoritative and unchanged.
"""
from __future__ import annotations

import datetime as dt
import json
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
    """Sort within established severity bands, using weights then provenance.

    This is ranking for *customer-story selection*, NOT quality scoring.
    Do not replace mandatory/legal admission, criticality, or customer gates.
    """
    severity = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}
    role_order = {"PREMIUM_OPPORTUNITY": 0, "PRECISION_DEMONSTRATION": 1, "BUSINESS_GAP": 2}

    def key(f: dict[str, Any]) -> tuple[Any, ...]:
        fid = str(f.get("id", ""))
        role = roles.get(fid, {}).get("role", "BUSINESS_GAP")
        return (
            severity.get(str(f.get("severity")), 9),
            -weights.get(str(f.get("category")), 0),
            role_order.get(role, 2),
            -int(f.get("confidence", 0)),
            fid,
        )

    return sorted(findings, key=key)
