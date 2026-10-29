#!/usr/bin/env python3
"""One customer reading per core metric, shared by every customer surface.

Strengths, lever admission, status matrices and category bars all ask this module how a metric reads to the
customer, so no two surfaces can interpret the same score differently (evidence-bound claims patch, owner
decisions 2026-10-29). Scores are never changed here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from customer_status import STATUS_META, customer_status
from legal_customer_projection import contested_identity_surface, contested_legal_surface

ROOT = Path(__file__).resolve().parents[1]


def registry_defs(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    data = json.loads((root / "assets/measurement-registry.json").read_text(encoding="utf-8"))
    return {str(m.get("id")): m for m in data.get("metrics", []) if isinstance(m, dict)}


def overlap_groups(root: Path = ROOT) -> list[frozenset[str]]:
    data = json.loads((root / "assets/customer-topic-overlaps.v1.json").read_text(encoding="utf-8"))
    return [frozenset(str(x) for x in g.get("metrics", [])) for g in data.get("groups", [])]


def contested_metrics(report: dict[str, Any]) -> frozenset[str]:
    """Metrics whose customer reading is suspended while a legal or provider-identity risk is projected."""
    return frozenset(contested_legal_surface(report)) | frozenset(contested_identity_surface(report))


def metric_reading(report: dict[str, Any], defs: dict[str, dict[str, Any]], metric: dict[str, Any]) -> dict[str, Any]:
    """The customer status of one metric plus why it reads that way.

    - contested by a projected legal/identity risk -> "Nicht belastbar bewertet" (the legal lever explains it);
    - presence-only and present -> "Nicht belastbar bewertet" with the label suffix "(vorhanden)": a presence
      check proves the page exists, not that its content is complete or compliant;
    - otherwise the score status.
    """
    mid = str(metric.get("id"))
    base = customer_status(metric)
    presence_only = defs.get(mid, {}).get("score_mode") == "presence_only"
    contested = mid in contested_metrics(report)
    present = presence_only and base["key"] not in {"ACTION", "UNASSESSED"}
    key = "UNASSESSED" if contested or present else base["key"]
    return {"key": key, **STATUS_META[key], "presence_only": presence_only, "present": present or (presence_only and contested),
            "contested": contested}


PRIMARY_UNASSESSED = frozenset({None, "", "not_assessed", "inferred_risk"})


def primary_metric(report: dict[str, Any], finding: dict[str, Any],
                   defs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """A finding's primary metric: its first cited metric that reads as a status to the customer.

    Refs outside not_assessed/inferred_risk that read "Nicht belastbar bewertet" (present presence checks,
    contested or unscored metrics) are skipped like not_assessed ones, so two refs with the same customer reading
    are interchangeable. Refs whose measurement_class is not_assessed, inferred_risk or missing are skipped by class;
    a class-less ref that carries a score would read "Klar" and still be skipped, so checklist B4 ("first cited")
    and this rule agree only while such refs read "Nicht belastbar bewertet", as all 48 do in the nine release cases.
    Lever admission and the surface-consistency gate both ask this.
    """
    defs = defs if defs is not None else registry_defs()
    metrics = {str(m.get("id")): m for m in report.get("metrics", []) if isinstance(m, dict)}
    for ref in finding.get("metric_refs", []) or []:
        metric = metrics.get(str(ref))
        if (metric is not None and metric.get("measurement_class") not in PRIMARY_UNASSESSED
                and metric_reading(report, defs, metric)["key"] != "UNASSESSED"):
            return metric
    return None


def readings(report: dict[str, Any], defs: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    defs = defs if defs is not None else registry_defs()
    return {str(m.get("id")): metric_reading(report, defs, m) for m in report.get("metrics", []) if isinstance(m, dict)}


def overlap_blocked(report: dict[str, Any], lever_metric_refs: set[str], defs: dict[str, dict[str, Any]] | None = None,
                    groups: list[frozenset[str]] | None = None) -> set[str]:
    """Metrics that must not vouch for their topic: a same-topic metric is a lever metric or reads Handlungsbedarf."""
    reads = readings(report, defs)
    blocked: set[str] = set()
    for group in groups if groups is not None else overlap_groups():
        for mid in group:
            siblings = group - {mid}
            if any(s in lever_metric_refs or reads.get(s, {}).get("key") == "ACTION" for s in siblings):
                blocked.add(mid)
    return blocked
