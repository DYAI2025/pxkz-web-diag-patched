#!/usr/bin/env python3
"""Deterministic business interpretation for Pixelkiez findings and metrics."""
from __future__ import annotations
from typing import Any

CATEGORY_MAP = {
    "findability_seo": ("Werden potenzielle Kunden auf das Unternehmen aufmerksam?", "FINDABILITY"),
    "search_visibility": ("Werden potenzielle Kunden auf das Unternehmen aufmerksam?", "FINDABILITY"),
    "crawl_indexability": ("Werden potenzielle Kunden auf das Unternehmen aufmerksam?", "FINDABILITY"),
    "information_architecture": ("Versteht ein Besucher sofort, was angeboten wird?", "UNDERSTANDING"),
    "content": ("Versteht ein Besucher sofort, was angeboten wird?", "UNDERSTANDING"),
    "ux_conversion": ("Wird aus Interesse einfach eine Anfrage?", "CONTACT_FRICTION"),
    "trust_privacy_content": ("Erzeugt die Website Vertrauen?", "TRUST"),
    "performance_tech": ("Funktioniert die Website technisch ohne unnötige Reibung?", "TECHNICAL_FRICTION"),
    "accessibility": ("Funktioniert die Website technisch ohne unnötige Reibung?", "RISK_REDUCTION"),
    "ai_readiness": ("Können KI-Systeme das Unternehmen eindeutig verstehen?", "AI_DISCOVERABILITY"),
    "entity_clarity": ("Können KI-Systeme das Unternehmen eindeutig verstehen?", "AI_DISCOVERABILITY"),
    "answerability": ("Können KI-Systeme das Unternehmen eindeutig verstehen?", "AI_DISCOVERABILITY"),
}

DEFAULT = ("Welche geschäftliche Wirkung hat dieser Befund?", "RISK_REDUCTION")


def business_axis(category: str) -> tuple[str, str]:
    return CATEGORY_MAP.get(str(category), DEFAULT)


def finding_business_record(finding: dict[str, Any]) -> dict[str, Any]:
    question, channel = business_axis(str(finding.get("category") or ""))
    relevance = finding.get("business_relevance") if isinstance(finding.get("business_relevance"), dict) else {}
    recommendation = finding.get("recommendation") if isinstance(finding.get("recommendation"), dict) else {}
    explanation = str(finding.get("client_impact") or relevance.get("text") or finding.get("client_observation") or finding.get("observation") or "").strip()
    action = str(finding.get("client_action") or recommendation.get("action") or "").strip()
    evidence_refs = []
    for item in finding.get("evidence", []) if isinstance(finding.get("evidence"), list) else []:
        if isinstance(item, dict) and item.get("id"):
            evidence_refs.append(str(item["id"]))
    return {
        "finding_id": str(finding.get("id") or ""),
        "business_question": question,
        "business_effect_channel": channel,
        "business_priority": str(finding.get("severity") or "medium").upper(),
        "business_explanation": explanation,
        "recommended_action": action,
        "action_type": str(recommendation.get("type") or "IMPROVEMENT"),
        "effort_class": recommendation.get("effort_class"),
        "evidence_refs": evidence_refs,
    }


def metric_business_interpretation(metric: dict[str, Any], label: str, category: str) -> dict[str, str]:
    question, channel = business_axis(category)
    status = str(metric.get("status") or "")
    value = metric.get("value")
    unit = str(metric.get("unit") or "").strip()
    if str(metric.get("measurement_class") or "") == "not_assessed" or status == "not_assessed":
        text = f"Für {label} liegt keine belastbare Aussage vor; daraus wird keine geschäftliche Wirkung behauptet."
    elif value not in (None, ""):
        text = f"{label} ist mit {value}{(' ' + unit) if unit else ''} dokumentiert. Die geschäftliche Einordnung erfolgt nur über belegte Findings."
    else:
        text = f"{label} ist dokumentiert. Die geschäftliche Einordnung erfolgt nur über belegte Findings."
    return {"business_question": question, "business_effect_channel": channel, "business_interpretation": text}
