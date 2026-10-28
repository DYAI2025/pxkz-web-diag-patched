#!/usr/bin/env python3
"""Strategic relevance gate for customer-visible Pixelkiez findings.

Internal evidence may be complete and verbose; customer-visible findings must describe an
assessed website/business condition that can change an entrepreneur's decision or action.
Validated non-core Impressum customer-risk findings use a separate legal evidence route and
must not be forced into the 48-metric core.
"""
from __future__ import annotations

import re
from typing import Any

from vibecheck03_admission import ROUTE as VC03_ROUTE
from vibecheck03_admission import evaluate_route as evaluate_vc03_route
from vibecheck03_admission import is_vc03_finding

STRATEGIC_QUESTION = (
    "H\u00e4tte ein Unternehmer, der mit dieser Website oder dem beworbenen Produkt/Service Geld verdient, "
    "einen strategischen Vorteil, wenn er diese Information kennt?"
)

PROCESS_ONLY_RX = re.compile(
    r"(?:audit[- ]?(?:coverage|abdeckung|prozess|umfang)|messabdeckung|testabdeckung|testumfang|pr\u00fcfumfang|"
    r"pr\u00fcfverfahren|evidence\s*grade|measurement\s*class|not_assessed|source_needed|validator|qa[- ]?status|"
    r"release[- ]?gate|pipeline|fixture|renderer|runtime|interner\s+pr\u00fcfprozess|interne\s+tests?)",
    re.I,
)

LEGAL_PRIORITIES = {"MANDATORY_CRITICAL", "MANDATORY_HIGH", "ELIGIBLE"}
LEGAL_STATES = {"ASSESSED_DEFECT", "POSSIBLE_LEGAL_REVIEW", "CONFLICT"}


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _metrics(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(m.get("id")): m for m in report.get("metrics", []) if isinstance(m, dict) and m.get("id")}


def _legal_route(finding: dict[str, Any], evidence: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    risk = finding.get("customer_risk") if isinstance(finding.get("customer_risk"), dict) else None
    if not risk:
        return False, []
    refs = [str(x) for x in risk.get("legal_metric_refs", []) if str(x).startswith("LEGAL-IMP-")]
    valid = (
        risk.get("source") == "impressum_compliance"
        and risk.get("domain") == "provider_identification"
        and risk.get("priority") in LEGAL_PRIORITIES
        and risk.get("claim_state") in LEGAL_STATES
        and bool(refs)
        and any(str(ev.get("type", "")) == "legal_sidecar" for ev in evidence if isinstance(ev, dict))
    )
    return valid, refs


def evaluate_finding(report: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic customer eligibility; never mutates the finding."""
    obs = _text(finding.get("client_observation") or finding.get("observation"))
    action = _text(finding.get("client_action") or (finding.get("recommendation") or {}).get("action"))
    impact = _text(finding.get("client_impact") or (finding.get("business_relevance") or {}).get("text"))
    title = _text(finding.get("title"))
    evidence = finding.get("evidence") if isinstance(finding.get("evidence"), list) else []
    refs = [str(x) for x in finding.get("metric_refs", []) if str(x).strip()]
    metrics = _metrics(report)
    linked = [metrics[x] for x in refs if x in metrics]
    legal_ok, legal_refs = _legal_route(finding, evidence)
    # Non-scoring VC03 diagnostics have their own route and may not borrow a core metric link;
    # only a fully valid legal sidecar route keeps precedence over it.
    vc03 = evaluate_vc03_route(report, finding) if is_vc03_finding(finding) and not legal_ok else None

    reasons: list[str] = []
    if not obs:
        reasons.append("NO_CLIENT_OBSERVATION")
    if not impact:
        reasons.append("NO_BUSINESS_IMPACT")
    if not action:
        reasons.append("NO_ACTION")
    if not evidence:
        reasons.append("NO_EVIDENCE")

    if vc03 is not None:
        reasons.extend(vc03["reasons"])
    elif legal_ok:
        pass
    elif not refs or not linked:
        reasons.append("NO_WEBSITE_OR_LEGAL_EVIDENCE_LINK")
    elif not any(str(m.get("measurement_class")) != "not_assessed" for m in linked):
        reasons.append("ONLY_NOT_ASSESSED_METRICS")

    process_surface = " ".join([title, obs, impact])
    if PROCESS_ONLY_RX.search(process_surface):
        reasons.append("INTERNAL_PROCESS_INFORMATION")
    result = {
        "eligible": not reasons,
        "question": STRATEGIC_QUESTION,
        "reasons": reasons or ["STRATEGIC_RELEVANCE_CONFIRMED"],
        "linked_assessed_metrics": [
            str(m.get("id")) for m in linked if str(m.get("measurement_class")) != "not_assessed"
        ] if vc03 is None else [],
        "linked_legal_refs": legal_refs if legal_ok and vc03 is None else [],
        "evidence_route": VC03_ROUTE if vc03 is not None else "LEGAL_SIDECAR" if legal_ok else "CORE_METRIC",
    }
    if vc03 is not None:
        result["linked_vc03_refs"] = vc03["vc03_refs"]
        result["vc03_rule_id"] = vc03["rule_id"]
    return result


def eligible_findings(report: dict[str, Any], *, include_positive: bool = False) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for finding in report.get("findings", []):
        if not isinstance(finding, dict):
            continue
        if not include_positive and finding.get("severity") == "positive":
            continue
        if evaluate_finding(report, finding)["eligible"]:
            out.append(finding)
    return out
