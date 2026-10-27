#!/usr/bin/env python3
"""Shared customer-visual selection policy for plan and PDF rendering."""
from __future__ import annotations

from typing import Any

CUSTOMER_MIN_VISUALS = 4
CUSTOMER_MAX_VISUALS = 7
CUSTOMER_TEMPLATE_PRIORITY = (
    "V01_OVERALL_SCORE",
    "V02_CATEGORY_BARS",
    "V03_TOP_LEVERS",
    "V07_PERFORMANCE_THRESHOLD",
    "V08_AI_ANSWERABILITY",
    "V10_TRUST_MATRIX",
    "V04_FINDABILITY_BENCHMARK",
    "V05_RANKING_POSITION",
    "V06_QUERY_COVERAGE",
    "V09_AGENT_READINESS",
    "V13_IMPACT_EFFORT",
    "V14_REPEAT_AUDIT",
    "V11_SEVERITY_DISTRIBUTION",
    "D01_PROCESS_FLOW",
)
_PRIORITY = {name: index for index, name in enumerate(CUSTOMER_TEMPLATE_PRIORITY)}


def order_customer_visuals(visuals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(visuals, key=lambda item: (_PRIORITY.get(str(item.get("template_id")), 999), str(item.get("id", ""))))


def apply_customer_visual_budget(visuals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = order_customer_visuals(visuals)
    return ordered[:CUSTOMER_MAX_VISUALS], ordered[CUSTOMER_MAX_VISUALS:]
