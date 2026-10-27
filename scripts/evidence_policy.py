#!/usr/bin/env python3
"""Deterministic truth policy for audit findings projected into voice-agent evidence classes."""
from __future__ import annotations

from typing import Any

VOICE_CLASSES = ("UNKNOWN", "HYPOTHESIS", "SUPPORTED_INFERENCE", "VERIFIED_FACT")
VOICE_RANK = {name: idx for idx, name in enumerate(VOICE_CLASSES)}
DIRECT_MEASUREMENT_CLASSES = {"measured", "observed"}
LOW_EVIDENCE_GRADES = {"E7", "E8"}


def _metric_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(metric.get("id")): metric
        for metric in report.get("metrics", [])
        if isinstance(metric, dict) and metric.get("id")
    }


def derive_voice_evidence_class(report: dict[str, Any], finding: dict[str, Any]) -> str:
    """Derive the strongest permissible voice class from canonical audit evidence.

    A finding may be weakened by a declared voice_hook.evidence_class, but that declaration
    can never upgrade the class derived from metric measurement classes/evidence grades.
    """
    refs = finding.get("metric_refs")
    metrics = _metric_map(report)

    if isinstance(refs, list) and refs:
        unresolved = [str(ref) for ref in refs if str(ref) not in metrics]
        if unresolved:
            raise ValueError(
                f"finding {finding.get('id')} has unresolved metric_refs: {', '.join(unresolved)}"
            )
        linked = [metrics[str(ref)] for ref in refs]
        classes = {str(metric.get("measurement_class", "")) for metric in linked}
        grades = {str(metric.get("evidence_grade", "")) for metric in linked}

        if "not_assessed" in classes:
            derived = "UNKNOWN"
        elif classes and classes <= {"inferred_risk"}:
            derived = "HYPOTHESIS"
        elif classes & DIRECT_MEASUREMENT_CLASSES and "inferred_risk" in classes:
            derived = "SUPPORTED_INFERENCE"
        elif classes and classes <= DIRECT_MEASUREMENT_CLASSES:
            # Direct observations with heuristic/unclear grades stay below VERIFIED_FACT.
            derived = "SUPPORTED_INFERENCE" if grades & LOW_EVIDENCE_GRADES else "VERIFIED_FACT"
        else:
            derived = "UNKNOWN"
    else:
        # Without metric bindings, the finding lacks the measurement-class axis needed for
        # VERIFIED_FACT. Existing finding evidence may support a cautious inference only.
        evidence = finding.get("evidence")
        derived = "SUPPORTED_INFERENCE" if isinstance(evidence, list) and evidence else "UNKNOWN"

    voice_hook = finding.get("voice_hook")
    declared = ""
    if isinstance(voice_hook, dict):
        declared = str(voice_hook.get("evidence_class") or "").strip()
    if declared:
        if declared not in VOICE_RANK:
            raise ValueError(f"finding {finding.get('id')} has invalid declared evidence class {declared!r}")
        if VOICE_RANK[declared] > VOICE_RANK[derived]:
            raise ValueError(
                f"finding {finding.get('id')} declares {declared} but canonical evidence permits at most {derived}"
            )
        # An explicit declaration may intentionally be more conservative than the derived cap.
        return declared
    return derived


def is_verified_voice_fact(report: dict[str, Any], finding: dict[str, Any]) -> bool:
    return derive_voice_evidence_class(report, finding) == "VERIFIED_FACT"
