#!/usr/bin/env python3
"""Business-first guardrails shared by the canonical visualization planner."""
from __future__ import annotations
from typing import Any

CUSTOMER_FORBIDDEN_TEMPLATES = {"V12_AUDIT_COVERAGE"}


def customer_allowed(visual: dict[str, Any]) -> tuple[bool, str]:
    tid = str(visual.get("template_id") or "")
    if tid in CUSTOMER_FORBIDDEN_TEMPLATES:
        return False, "INTERNAL_MEASUREMENT_VISUAL"
    return True, "BUSINESS_RELEVANT"


def business_population(label: str, count: int | None = None) -> str:
    return f"{count} dokumentierte Werte" if isinstance(count, int) else str(label)
