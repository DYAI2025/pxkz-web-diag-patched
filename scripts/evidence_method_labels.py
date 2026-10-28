#!/usr/bin/env python3
"""Canonical evidence-method classification for customer projection.

A customer sentence may be simplified, but the measurement method must survive:
LAB (technical test run, no real users), FIELD (real-user data) or SYNTHETIC (fixture or
example data that must never be presented as a live measurement).
"""
from __future__ import annotations

import re
from typing import Any

METHOD_PHRASES: dict[str, str] = {
    "LAB": "technische Testmessung, keine realen Nutzerdaten",
    "FIELD": "reale Nutzerdaten",
    "SYNTHETIC": "Beispieldaten, keine Live-Messung",
}
SHORT_LABELS: dict[str, str] = {"LAB": "Testmessung", "FIELD": "reale Nutzerdaten", "SYNTHETIC": "Beispieldaten"}

SYNTHETIC_RX = re.compile(r"synthetic|synthetis", re.IGNORECASE)
FIELD_RX = re.compile(r"\bCrUX\b|Chrome UX|Felddaten|\bfield\b", re.IGNORECASE)


def _item_dict(item: dict[str, Any] | None, key: str) -> dict[str, Any]:
    value = item.get(key) if isinstance(item, dict) else None
    return value if isinstance(value, dict) else {}


def evidence_method(metric: dict[str, Any], item: dict[str, Any] | None = None) -> str:
    """Classify the evidence behind one plotted metric value. Synthetic wins over everything."""
    ev, thr = _item_dict(item, "evidence"), _item_dict(item, "threshold")
    texts = [str(x or "") for x in (
        metric.get("source_or_method"), metric.get("threshold_source"), metric.get("does_not_prove"),
        ev.get("tool"), ev.get("method"), thr.get("source"), (item or {}).get("metric_label"),
    )]
    value = metric.get("value")
    structural_fixture = (
        "FIXTURE" in str(metric.get("note") or "").upper()
        or (isinstance(value, dict) and value.get("fixture") is True)
        or str(ev.get("mode") or "").upper() in {"FIXTURE", "SYNTHETIC"}
    )
    if structural_fixture or any(SYNTHETIC_RX.search(t) for t in texts):
        return "SYNTHETIC"
    # Limitation texts ("Lab result is not real-user field performance.") name what the value is NOT.
    method_texts = [str(x or "") for x in (metric.get("source_or_method"), ev.get("tool"), ev.get("method"))]
    if str(ev.get("mode") or "").upper() == "FIELD" or any(FIELD_RX.search(t) for t in method_texts):
        return "FIELD"
    return "LAB"


def method_phrase(kind: str) -> str:
    return METHOD_PHRASES[kind]


def short_label(kind: str) -> str:
    return SHORT_LABELS[kind]
