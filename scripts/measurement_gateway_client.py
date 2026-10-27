#!/usr/bin/env python3
"""Read a versioned measurement envelope from an optional Pixelkiez gateway."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 1_048_576


class MeasurementGatewayError(RuntimeError):
    pass


def _validate_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise MeasurementGatewayError("invalid gateway endpoint")
    if parsed.username is not None or parsed.password is not None:
        raise MeasurementGatewayError("credential-bearing gateway endpoint is forbidden")
    host = parsed.hostname.lower()
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise MeasurementGatewayError("non-loopback gateway endpoints require https")
    return endpoint.rstrip("/")


def fetch_envelope(endpoint: str, target_url: str, *, timeout_seconds: float = 15.0) -> dict[str, Any]:
    endpoint = _validate_endpoint(endpoint)
    body = json.dumps({"target_url": target_url}, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint + "/v1/audit",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "PixelkiezWebsiteDiagnosis/measurement-gateway-client-v1"},
    )
    try:
        with urlopen(request, timeout=float(timeout_seconds)) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        if not raw:
            raise MeasurementGatewayError(f"gateway HTTP error {exc.code}") from exc
    except URLError as exc:
        raise MeasurementGatewayError(f"gateway unavailable: {type(exc.reason).__name__}") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise MeasurementGatewayError("gateway response too large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise MeasurementGatewayError("gateway returned invalid JSON") from exc
    if not isinstance(payload, dict) or "schema_version" not in payload:
        raise MeasurementGatewayError("gateway response is not a measurement envelope")
    return payload


def configured_endpoint(config: dict[str, Any]) -> str | None:
    block = config.get("measurement_gateway") if isinstance(config.get("measurement_gateway"), dict) else {}
    value = block.get("endpoint") or os.getenv("PIXELKIEZ_MEASUREMENT_GATEWAY_URL")
    return str(value).strip() if value else None
