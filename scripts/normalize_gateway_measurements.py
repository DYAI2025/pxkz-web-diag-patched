#!/usr/bin/env python3
"""Normalize approved gateway observations into existing measurement enrichment records."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

from measurement_enrichment import metric_record

MAPPING = {
    "HTTP_STATUS_CODE": ("PUBLIC_HTTP_STATUS_CODE", "MEASURED"),
    "REDIRECT_COUNT": ("PUBLIC_REDIRECT_COUNT", "MEASURED"),
    "HTTPS_FINAL": ("PUBLIC_HTTPS_FINAL", "OBSERVED"),
    "TLS_VERIFIED": ("PUBLIC_TLS_VERIFIED", "OBSERVED"),
    "ROBOTS_PRESENT": ("PUBLIC_ROBOTS_PRESENT", "OBSERVED"),
    "SITEMAP_PRESENT": ("PUBLIC_SITEMAP_PRESENT", "OBSERVED"),
    "CSP_PRESENT": ("PUBLIC_CSP_PRESENT", "OBSERVED"),
    "CSP_RISK_COUNT": ("PUBLIC_CSP_RISK_COUNT", "MEASURED"),
    "SECURITY_HEADERS_PRESENT_COUNT": ("PUBLIC_SECURITY_HEADERS_PRESENT_COUNT", "MEASURED"),
}


def normalize_envelope(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("status") not in {"COMPLETE", "PARTIAL"}:
        return []
    source_type = "FIXTURE_REPLAY" if payload.get("execution_mode") == "FIXTURE" else "PUBLIC_API"
    provider = f"Pixelkiez Measurement Gateway {payload.get('gateway_version') or ''}".strip()
    rows: list[dict[str, Any]] = []
    for obs in payload.get("observations", []):
        if not isinstance(obs, dict) or obs.get("id") not in MAPPING:
            continue
        metric_id, default_status = MAPPING[str(obs["id"])]
        obs_status = str(obs.get("status") or default_status)
        status = default_status if obs_status in {"MEASURED", "OBSERVED"} else obs_status
        rows.append(metric_record(
            metric_id,
            status=status,
            value=obs.get("value"),
            source_type=source_type,
            source_provider=provider,
            observed_at=obs.get("observed_at"),
            url=obs.get("url") or payload.get("target_url"),
            evidence_ref=f"{payload.get('run_id')}:{obs.get('evidence_ref')}",
            context={
                "gateway_run_id": payload.get("run_id"),
                "gateway_execution_mode": payload.get("execution_mode"),
                "gateway_adapter": obs.get("adapter"),
                "gateway_context": obs.get("context") if isinstance(obs.get("context"), dict) else {},
                "gateway_claim_boundary": obs.get("claim_boundary"),
            },
        ))
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("FAIL: usage: normalize_gateway_measurements.py <envelope.json> <metrics.json>", file=sys.stderr)
        return 1
    try:
        payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        rows = normalize_envelope(payload)
        Path(argv[2]).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: normalized gateway observations={len(rows)}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
