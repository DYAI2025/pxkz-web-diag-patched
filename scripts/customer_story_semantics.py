#!/usr/bin/env python3
"""Deterministic scan-first semantic policy for Pixelkiez customer findings.

This module does not invent or rewrite audit facts. It chooses a presentation mode from
already validated evidence, extracts direct quantitative signals when safe, and applies
simple anti-generic/scanability gates. Natural-language quality remains bounded by source
client_* fields plus final vision/human semantic review.
"""
from __future__ import annotations

import re
from typing import Any

from client_story import clientize

DIRECT_CLASSES = {"measured", "observed"}
BLOCKED_GRADES = {"E7", "E8"}
PRESENTATION_MODES = {"NUMBER_FIRST", "EVIDENCE_VISUAL", "SHORT_TEXT"}

TECH_JARGON = re.compile(
    r"\b(?:LCP|INP|CLS|TTFB|CTA|SERP|JSON-LD|Raw DOM|Raw-HTML|Redirects?|Canonicals?|CrUX|PSI|Lighthouse|PageSpeed|WCAG|Viewport|Deployment)\b|robots\.txt|sitemap\.xml",
    re.I,
)

GENERIC_COPY = re.compile(
    r"\b(?:optimierungspotenzial|verbesserungspotenzial|handlungsbedarf|"
    r"k(?:ö|oe)nnte verbessert werden|kann verbessert werden|nicht optimal|suboptimal|"
    r"ausbauf(?:ä|ae)hig|sollte optimiert werden|bereich optimieren|allgemein verbessern)\b",
    re.I,
)

RATIO = re.compile(r"^\s*(\d+)\s*(?:of|von|/)\s*(\d+)\b", re.I)
PERCENT = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*%\s*$")
NUMBER_WITH_UNIT = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*([a-zA-Z%]+)?\s*$")


def _de_number(value: float | int) -> str:
    if isinstance(value, float) and not value.is_integer():
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        text = str(int(value))
    return text.replace(".", ",")


def direct_display_value(value: Any, unit: Any = None) -> str | None:
    """Return a concise display value only for directly numeric/ratio-shaped evidence."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        base = _de_number(value)
        u = str(unit or "").strip()
        return f"{base} {u}".strip()
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    m = RATIO.match(text)
    if m:
        return f"{m.group(1)} von {m.group(2)}"
    m = PERCENT.match(text)
    if m:
        raw = m.group(1).replace(".", ",")
        return f"{raw} %"
    m = NUMBER_WITH_UNIT.match(text)
    if m and m.group(2):
        raw = m.group(1).replace(".", ",")
        return f"{raw} {m.group(2)}"
    return None


def _registry_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(x.get("id")): x for x in registry.get("metrics", []) if isinstance(x, dict) and x.get("id")}


def _metric_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(x.get("id")): x for x in report.get("metrics", []) if isinstance(x, dict) and x.get("id")}


def numeric_signal(report: dict[str, Any], finding: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any] | None:
    """Choose one direct, customer-readable quantitative signal tied to this finding.

    Prefer measured over observed. Never use inferred_risk/not_assessed, E7/E8, an internal
    score as a substitute for a real value, or a value that is not actually numeric/ratio-shaped.
    """
    metrics = _metric_map(report)
    defs = _registry_map(registry)
    candidates: list[tuple[int, int, str, dict[str, Any], dict[str, Any], str]] = []
    for order, ref in enumerate(finding.get("metric_refs", []) if isinstance(finding.get("metric_refs"), list) else []):
        mid = str(ref)
        metric = metrics.get(mid)
        if not metric:
            continue
        mclass = str(metric.get("measurement_class", ""))
        if mclass not in DIRECT_CLASSES or metric.get("evidence_grade") in BLOCKED_GRADES:
            continue
        display = direct_display_value(metric.get("value"), metric.get("unit"))
        if not display:
            continue
        rank = 0 if mclass == "measured" else 1
        confidence = int(metric.get("confidence", 0)) if isinstance(metric.get("confidence"), int) else 0
        candidates.append((rank, -confidence, order, metric, defs.get(mid, {}), display))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    _, _, _, metric, mdef, display = candidates[0]
    mid = str(metric.get("id"))
    return {
        "metric_ref": mid,
        "label": clientize(mdef.get("label_de") or mid, 80),
        "display_value": display,
        "raw_value": metric.get("value"),
        "unit": metric.get("unit"),
        "measurement_class": metric.get("measurement_class"),
        "evidence_grade": metric.get("evidence_grade"),
        "source_or_method": str(metric.get("source_or_method") or ""),
        "does_not_prove": clientize(metric.get("does_not_prove") or "", 180),
    }


def specificity_basis(finding: dict[str, Any], signal: dict[str, Any] | None) -> list[str]:
    basis: list[str] = []
    if signal:
        basis.append(f"metric:{signal['metric_ref']}")
    for ref in finding.get("metric_refs", []) if isinstance(finding.get("metric_refs"), list) else []:
        token = f"metric:{ref}"
        if token not in basis:
            basis.append(token)
    for ev in finding.get("evidence", []) if isinstance(finding.get("evidence"), list) else []:
        if not isinstance(ev, dict):
            continue
        if ev.get("id"):
            basis.append(f"evidence:{ev['id']}")
        if ev.get("url"):
            basis.append(f"url:{ev['url']}")
    return basis[:6]


def presentation_metadata(report: dict[str, Any], finding: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    signal = numeric_signal(report, finding, registry)
    evidence = [x for x in finding.get("evidence", []) if isinstance(x, dict)] if isinstance(finding.get("evidence"), list) else []
    if signal:
        mode = "NUMBER_FIRST"
    elif len(evidence) >= 2:
        mode = "EVIDENCE_VISUAL"
    else:
        mode = "SHORT_TEXT"
    return {
        "presentation_mode": mode,
        "numeric_signal": signal,
        "specificity_basis": specificity_basis(finding, signal),
    }


def source_finding_semantic_errors(finding: dict[str, Any]) -> list[str]:
    """Validate source client_* fields before client-model projection."""
    errors: list[str] = []
    fid = str(finding.get("id", "finding"))
    fields = {
        "client_observation": (130, str(finding.get("client_observation") or "")),
        "client_impact": (135, str(finding.get("client_impact") or "")),
        "client_action": (125, str(finding.get("client_action") or "")),
    }
    for name, (limit, text) in fields.items():
        text = " ".join(text.split())
        if not text:
            errors.append(f"{fid} {name} missing")
            continue
        if len(text) > limit:
            errors.append(f"{fid} {name} exceeds scan-first limit {limit}")
        if GENERIC_COPY.search(text):
            errors.append(f"{fid} {name} contains generic agency wording")
        if TECH_JARGON.search(text):
            errors.append(f"{fid} {name} contains customer-facing technical jargon")
    return errors


def model_finding_semantic_errors(finding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fid = str(finding.get("id", "finding"))
    mode = str(finding.get("presentation_mode", ""))
    if mode not in PRESENTATION_MODES:
        errors.append(f"{fid} invalid presentation_mode")
    limits = {"headline": 110, "observation": 130, "impact": 135, "action": 125}
    for name, limit in limits.items():
        text = " ".join(str(finding.get(name) or "").split())
        if not text:
            errors.append(f"{fid} {name} missing")
        elif len(text) > limit:
            errors.append(f"{fid} {name} exceeds scan-first limit {limit}")
        if GENERIC_COPY.search(text):
            errors.append(f"{fid} {name} contains generic agency wording")
        if TECH_JARGON.search(text):
            errors.append(f"{fid} {name} contains customer-facing technical jargon")
    basis = finding.get("specificity_basis")
    if not isinstance(basis, list) or not basis:
        errors.append(f"{fid} specificity_basis missing")
    signal = finding.get("numeric_signal")
    if mode == "NUMBER_FIRST":
        if not isinstance(signal, dict):
            errors.append(f"{fid} NUMBER_FIRST requires numeric_signal")
        elif signal.get("measurement_class") not in DIRECT_CLASSES or signal.get("evidence_grade") in BLOCKED_GRADES:
            errors.append(f"{fid} numeric_signal is not direct supported evidence")
        elif not str(signal.get("display_value") or "").strip():
            errors.append(f"{fid} numeric_signal display_value missing")
    elif signal is not None:
        errors.append(f"{fid} non-NUMBER_FIRST finding must not carry numeric_signal")
    return errors


def semantic_story_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    counts = {mode: 0 for mode in sorted(PRESENTATION_MODES)}
    numeric = 0
    for finding in findings:
        ferr = model_finding_semantic_errors(finding)
        errors.extend(ferr)
        mode = str(finding.get("presentation_mode", ""))
        if mode in counts:
            counts[mode] += 1
        if isinstance(finding.get("numeric_signal"), dict):
            numeric += 1
    return {
        "policy_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "finding_count": len(findings),
        "presentation_mode_counts": counts,
        "quantitative_signal_count": numeric,
        "scan_first_limits": {"headline": 110, "observation": 130, "impact": 135, "action": 125},
        "errors": errors,
    }
