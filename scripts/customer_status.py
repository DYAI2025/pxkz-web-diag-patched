#!/usr/bin/env python3
"""Customer-facing four-state status semantics for Pixelkiez visuals."""
from __future__ import annotations
from typing import Any

STATUS_META = {
    "CLEAR": {"label": "Klar", "symbol": "OK", "value": 1.0, "tone": "good"},
    "IMPROVE": {"label": "Verbesserung sinnvoll", "symbol": "!", "value": 0.66, "tone": "warn"},
    "ACTION": {"label": "Handlungsbedarf", "symbol": "X", "value": 0.0, "tone": "bad"},
    "UNASSESSED": {"label": "Nicht belastbar bewertet", "symbol": "-", "value": 0.42, "tone": "neutral"},
}

def customer_status(metric: dict[str, Any]) -> dict[str, Any]:
    mc = str(metric.get("measurement_class") or "")
    state = str(metric.get("status") or "")
    score = metric.get("score")
    if mc == "not_assessed" or state in {"not_assessed", "not_applicable"} or score is None:
        key = "UNASSESSED"
    elif state in {"blocking", "weak"} or (isinstance(score, (int,float)) and not isinstance(score, bool) and score < 50):
        key = "ACTION"
    elif state in {"mixed", "minor_gaps"} or (isinstance(score, (int,float)) and not isinstance(score, bool) and score < 75):
        key = "IMPROVE"
    else:
        key = "CLEAR"
    return {"key": key, **STATUS_META[key]}
