#!/usr/bin/env python3
"""Shared contracts for optional Pixelkiez measurement enrichment."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "assets" / "enrichment-metric-registry.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_registry() -> dict[str, dict[str, Any]]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {str(x["id"]): x for x in data.get("metrics", [])}


REGISTRY = load_registry()


def metric_record(
    metric_id: str,
    *,
    status: str,
    value: Any = None,
    source_type: str,
    source_provider: str,
    observed_at: str | None = None,
    url: str | None = None,
    query: str | None = None,
    market: str | None = None,
    location: str | None = None,
    device: str | None = None,
    date_range: dict[str, str] | None = None,
    evidence_ref: str,
    context: dict[str, Any] | None = None,
    manual_review_required: bool = False,
    legal_review_required: bool = False,
) -> dict[str, Any]:
    if metric_id not in REGISTRY:
        raise KeyError(f"unknown enrichment metric: {metric_id}")
    definition = REGISTRY[metric_id]
    if status in {"MEASURED", "OBSERVED"}:
        measurement_class = "measured" if status == "MEASURED" else "observed"
        if observed_at is None:
            observed_at = now_iso()
    else:
        measurement_class = "not_assessed"
        value = None
        observed_at = None
    return {
        "id": metric_id,
        "family": definition["family"],
        "label": definition["label_de"],
        "status": status,
        "measurement_class": measurement_class,
        "value": value,
        "unit": definition.get("unit"),
        "source_type": source_type,
        "source_provider": source_provider,
        "observed_at": observed_at,
        "date_range": date_range,
        "url": url,
        "query": query,
        "market": market,
        "location": location,
        "device": device,
        "evidence_ref": evidence_ref,
        "claim_boundary": definition["does_not_prove"],
        "manual_review_required": bool(manual_review_required),
        "legal_review_required": bool(legal_review_required),
        "context": context or {},
    }


def source_record(source_id: str, provider: str, status: str, note: str = "") -> dict[str, str]:
    return {"id": source_id, "provider": provider, "status": status, "note": note}


def bundle(target_url: str, mode: str, sources: list[dict[str, Any]], metrics: list[dict[str, Any]], generated_at: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "target_url": target_url,
        "generated_at": generated_at or now_iso(),
        "mode": mode,
        "sources": sources,
        "metrics": metrics,
    }


def metric_index(enrichment: dict[str, Any]) -> dict[tuple[str, str | None, str | None], dict[str, Any]]:
    out: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for row in enrichment.get("metrics", []):
        if isinstance(row, dict):
            out[(str(row.get("id")), row.get("query"), row.get("device"))] = row
    return out
