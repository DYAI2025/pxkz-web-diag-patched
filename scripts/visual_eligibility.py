#!/usr/bin/env python3
"""Classify customer information into an approved business-first visual form."""
from __future__ import annotations
from typing import Any

APPROVED = {"BIG_NUMBER","BULLET_BAR","HORIZONTAL_BAR","RANKING","BENCHMARK","STATUS_MATRIX","EVIDENCE_COMPARE","PRIORITY_MATRIX","SHORT_TEXT"}


def classify(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("query") and isinstance(item.get("position"), int):
        visual = "RANKING"
    elif item.get("comparison_entities") or item.get("entities"):
        visual = "BENCHMARK"
    elif item.get("priority") and item.get("effort"):
        visual = "PRIORITY_MATRIX"
    elif isinstance(item.get("value"), (int, float)) and not isinstance(item.get("value"), bool):
        visual = "BULLET_BAR" if item.get("target") is not None else "BIG_NUMBER"
    elif item.get("status") in {"yes","no","partial","klar","teilweise","offen",True,False}:
        visual = "STATUS_MATRIX"
    elif item.get("before") is not None and item.get("after") is not None:
        visual = "EVIDENCE_COMPARE"
    else:
        visual = "SHORT_TEXT"
    return {"visual_type": visual, "reason": "deterministic data-shape routing", "eligible": visual in APPROVED}
