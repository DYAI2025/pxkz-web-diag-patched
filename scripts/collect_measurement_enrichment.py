#!/usr/bin/env python3
"""Collect optional Pixelkiez measurement enrichment from read-only APIs/browser or fixtures."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from browser_measurements import collect_browser_metrics
from measurement_adapters import (
    fetch_crux,
    fetch_dataforseo,
    fetch_ga4_event,
    fetch_ga4_summary,
    fetch_gsc_inspection,
    fetch_gsc_query,
    fetch_pagespeed,
    parse_crux,
    parse_dataforseo,
    parse_ga4_event,
    parse_ga4_summary,
    parse_gsc_inspection,
    parse_gsc_query,
    parse_pagespeed,
)
from measurement_enrichment import bundle, source_record
from measurement_gateway_client import configured_endpoint, fetch_envelope
from normalize_gateway_measurements import normalize_envelope


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain object")
    return data


def safe_get(obj: dict[str, Any] | None, *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def add_source(sources: list[dict[str, Any]], source_id: str, provider: str, status: str, note: str = "") -> None:
    sources.append(source_record(source_id, provider, status, note))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target_url")
    ap.add_argument("output")
    ap.add_argument("--config", required=True, help="non-secret measurement config JSON")
    ap.add_argument("--fixture-bundle", help="provider response bundle for deterministic replay")
    ap.add_argument("--offline", action="store_true", help="do not make network calls; unfixture providers become unavailable")
    args = ap.parse_args(argv[1:])
    try:
        config = load_json(Path(args.config))
        fixtures = load_json(Path(args.fixture_bundle)) if args.fixture_bundle else None
        target_url = args.target_url
        metrics: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        mode = "FIXTURE" if fixtures is not None else ("OFFLINE" if args.offline else "LIVE")

        # PageSpeed / Lighthouse lab
        psi = config.get("pagespeed") if isinstance(config.get("pagespeed"), dict) else {}
        strategies = psi.get("strategies", ["mobile", "desktop"]) if psi.get("enabled", True) else []
        if strategies:
            key = os.getenv("PIXELKIEZ_PAGESPEED_API_KEY")
            ok = 0
            errors = []
            for strategy in strategies:
                try:
                    if fixtures is not None and safe_get(fixtures, "pagespeed", str(strategy)) is not None:
                        metrics += parse_pagespeed(safe_get(fixtures, "pagespeed", str(strategy)), target_url, str(strategy), source_type="FIXTURE_REPLAY", evidence_prefix=f"FIX-PSI-{strategy}")
                    elif args.offline:
                        raise RuntimeError("offline and no fixture")
                    elif not key:
                        raise RuntimeError("PIXELKIEZ_PAGESPEED_API_KEY not configured")
                    else:
                        _, rows = fetch_pagespeed(target_url, key, str(strategy)); metrics += rows
                    ok += 1
                except Exception as exc:
                    errors.append(f"{strategy}:{exc}")
            add_source(sources, "pagespeed", "Google PageSpeed Insights / Lighthouse", "AVAILABLE" if ok else ("NOT_CONFIGURED" if any("not configured" in x for x in errors) else "UNAVAILABLE"), "; ".join(errors))

        # CrUX field data
        crux = config.get("crux") if isinstance(config.get("crux"), dict) else {}
        factors = crux.get("form_factors", ["PHONE", "DESKTOP"]) if crux.get("enabled", True) else []
        if factors:
            key = os.getenv("PIXELKIEZ_CRUX_API_KEY")
            ok = 0
            errors = []
            for factor in factors:
                try:
                    if fixtures is not None and safe_get(fixtures, "crux", str(factor)) is not None:
                        metrics += parse_crux(safe_get(fixtures, "crux", str(factor)), target_url, str(factor), source_type="FIXTURE_REPLAY", evidence_prefix=f"FIX-CRUX-{factor}")
                    elif args.offline:
                        raise RuntimeError("offline and no fixture")
                    elif not key:
                        raise RuntimeError("PIXELKIEZ_CRUX_API_KEY not configured")
                    else:
                        _, rows = fetch_crux(target_url, key, str(factor)); metrics += rows
                    ok += 1
                except Exception as exc:
                    errors.append(f"{factor}:{exc}")
            add_source(sources, "crux", "Chrome UX Report API", "AVAILABLE" if ok else ("NOT_CONFIGURED" if any("not configured" in x for x in errors) else "UNAVAILABLE"), "; ".join(errors))

        # Search Console Search Analytics + URL inspection
        gsc = config.get("search_console") if isinstance(config.get("search_console"), dict) else {}
        if gsc.get("enabled"):
            token = os.getenv("PIXELKIEZ_GOOGLE_ACCESS_TOKEN")
            site_url = str(gsc.get("site_url") or "")
            start_date = str(gsc.get("start_date") or "28daysAgo")
            end_date = str(gsc.get("end_date") or "yesterday")
            queries = [x for x in gsc.get("queries", []) if isinstance(x, dict) and x.get("query")]
            ok = 0; errors = []
            for i, q in enumerate(queries):
                query = str(q["query"])
                try:
                    fp = safe_get(fixtures, "search_console", "queries", query) if fixtures is not None else None
                    if fp is not None:
                        metrics += parse_gsc_query(fp, target_url, query, start_date, end_date, location=q.get("country"), device=q.get("device"), source_type="FIXTURE_REPLAY", evidence_prefix=f"FIX-GSC-{i+1}")
                    elif args.offline:
                        raise RuntimeError("offline and no fixture")
                    elif not token:
                        raise RuntimeError("PIXELKIEZ_GOOGLE_ACCESS_TOKEN not configured")
                    elif not site_url:
                        raise RuntimeError("search_console.site_url missing")
                    else:
                        _, rows = fetch_gsc_query(site_url, target_url, query, start_date, end_date, token, device=q.get("device"), country=q.get("country")); metrics += rows
                    ok += 1
                except Exception as exc:
                    errors.append(f"query:{query}:{exc}")
            try:
                fp = safe_get(fixtures, "search_console", "inspection") if fixtures is not None else None
                if fp is not None:
                    metrics += parse_gsc_inspection(fp, target_url, source_type="FIXTURE_REPLAY", evidence_prefix="FIX-GSC-INSPECT")
                    ok += 1
                elif not args.offline and token and site_url:
                    _, rows = fetch_gsc_inspection(site_url, target_url, token); metrics += rows; ok += 1
                else:
                    raise RuntimeError("URL inspection not configured/fixture unavailable")
            except Exception as exc:
                errors.append(f"inspection:{exc}")
            add_source(sources, "search_console", "Google Search Console", "AVAILABLE" if ok else ("NOT_CONFIGURED" if not token and fixtures is None else "UNAVAILABLE"), "; ".join(errors))

        # GA4 stable runReport summaries and configured event counts
        ga4 = config.get("ga4") if isinstance(config.get("ga4"), dict) else {}
        if ga4.get("enabled"):
            token = os.getenv("PIXELKIEZ_GOOGLE_ACCESS_TOKEN")
            prop = str(ga4.get("property_id") or "")
            start_date = str(ga4.get("start_date") or "28daysAgo")
            end_date = str(ga4.get("end_date") or "yesterday")
            ok = 0; errors = []
            try:
                fp = safe_get(fixtures, "ga4", "summary") if fixtures is not None else None
                if fp is not None:
                    metrics += parse_ga4_summary(fp, target_url, start_date, end_date, source_type="FIXTURE_REPLAY", evidence_prefix="FIX-GA4")
                elif args.offline:
                    raise RuntimeError("offline and no fixture")
                elif not token:
                    raise RuntimeError("PIXELKIEZ_GOOGLE_ACCESS_TOKEN not configured")
                elif not prop:
                    raise RuntimeError("ga4.property_id missing")
                else:
                    _, rows = fetch_ga4_summary(prop, target_url, start_date, end_date, token); metrics += rows
                ok += 1
            except Exception as exc:
                errors.append(f"summary:{exc}")
            event_map = ga4.get("event_names", {}) if isinstance(ga4.get("event_names"), dict) else {}
            for canonical, configured in event_map.items():
                try:
                    fp = safe_get(fixtures, "ga4", "events", str(canonical)) if fixtures is not None else None
                    if fp is not None:
                        metrics += parse_ga4_event(fp, target_url, start_date, end_date, str(canonical), str(configured), source_type="FIXTURE_REPLAY", evidence_prefix="FIX-GA4-EVENT")
                    elif args.offline:
                        raise RuntimeError("offline and no fixture")
                    elif not token or not prop:
                        raise RuntimeError("GA4 auth/property not configured")
                    else:
                        _, rows = fetch_ga4_event(prop, target_url, start_date, end_date, token, str(canonical), str(configured)); metrics += rows
                    ok += 1
                except Exception as exc:
                    errors.append(f"event:{canonical}:{exc}")
            add_source(sources, "ga4", "Google Analytics Data API", "AVAILABLE" if ok else ("NOT_CONFIGURED" if not token and fixtures is None else "UNAVAILABLE"), "; ".join(errors))

        # Query-specific current SERP observation
        serp = config.get("serp") if isinstance(config.get("serp"), dict) else {}
        if serp.get("enabled"):
            login, password = os.getenv("PIXELKIEZ_DATAFORSEO_LOGIN"), os.getenv("PIXELKIEZ_DATAFORSEO_PASSWORD")
            queries = [x for x in serp.get("queries", []) if isinstance(x, dict) and x.get("query")]
            ok = 0; errors = []
            for i, q in enumerate(queries):
                query = str(q["query"])
                try:
                    fp = safe_get(fixtures, "dataforseo", "queries", query) if fixtures is not None else None
                    if fp is not None:
                        metrics += parse_dataforseo(fp, target_url, query, requested_location=str(q.get("location_name") or q.get("location_code") or ""), requested_device=str(q.get("device") or "desktop"), source_type="FIXTURE_REPLAY", evidence_prefix=f"FIX-DFS-{i+1}")
                    elif args.offline:
                        raise RuntimeError("offline and no fixture")
                    elif not login or not password:
                        raise RuntimeError("PIXELKIEZ_DATAFORSEO_LOGIN/PASSWORD not configured")
                    else:
                        _, rows = fetch_dataforseo(target_url, query, login, password, location_code=q.get("location_code"), location_name=q.get("location_name"), language_code=str(q.get("language_code") or "de"), device=str(q.get("device") or "desktop"), os_name=q.get("os"), depth=int(q.get("depth") or 100)); metrics += rows
                    ok += 1
                except Exception as exc:
                    errors.append(f"{query}:{exc}")
            add_source(sources, "serp", "DataForSEO Google Organic Live Advanced", "AVAILABLE" if ok else ("NOT_CONFIGURED" if (not login or not password) and fixtures is None else "UNAVAILABLE"), "; ".join(errors))

        # Optional Pixelkiez Measurement Gateway public-probe slice
        gateway_cfg = config.get("measurement_gateway") if isinstance(config.get("measurement_gateway"), dict) else {}
        if gateway_cfg.get("enabled"):
            try:
                envelope = safe_get(fixtures, "measurement_gateway") if fixtures is not None else None
                if envelope is None:
                    if args.offline:
                        raise RuntimeError("offline and no gateway fixture")
                    endpoint = configured_endpoint(config)
                    if not endpoint:
                        raise RuntimeError("measurement gateway endpoint not configured")
                    envelope = fetch_envelope(endpoint, target_url, timeout_seconds=float(gateway_cfg.get("timeout_seconds") or 15))
                metrics += normalize_envelope(envelope)
                state = str(envelope.get("status") or "UNAVAILABLE")
                source_status = "AVAILABLE" if state in {"COMPLETE", "PARTIAL"} else "UNAVAILABLE"
                errors = envelope.get("errors") if isinstance(envelope.get("errors"), list) else []
                note = f"mode={envelope.get('execution_mode')} status={state} run_id={envelope.get('run_id')}"
                if errors:
                    note += "; errors=" + ",".join(str(x.get("code") or "ERROR") for x in errors if isinstance(x, dict))
                add_source(sources, "measurement_gateway", "Pixelkiez Measurement Gateway", source_status, note)
            except Exception as exc:
                status = "NOT_CONFIGURED" if "not configured" in str(exc).lower() else "UNAVAILABLE"
                add_source(sources, "measurement_gateway", "Pixelkiez Measurement Gateway", status, str(exc))

        # Public browser module (never private/login areas)
        browser_cfg = config.get("browser") if isinstance(config.get("browser"), dict) else {}
        if browser_cfg.get("enabled"):
            try:
                if fixtures is not None and safe_get(fixtures, "browser_enrichment") is not None:
                    b = safe_get(fixtures, "browser_enrichment")
                    metrics += [x for x in b.get("metrics", []) if isinstance(x, dict)]
                    add_source(sources, "browser", "Chromium/Playwright fixture replay", "AVAILABLE", "fixture replay")
                elif args.offline and not target_url.startswith(("file://", "http://127.0.0.1", "http://localhost")):
                    add_source(sources, "browser", "Chromium/Playwright", "UNAVAILABLE", "offline mode permits browser only for local fixture URLs")
                else:
                    rows, details = collect_browser_metrics(target_url, wait_ms=int(browser_cfg.get("wait_ms") or 800), timeout_ms=int(browser_cfg.get("timeout_ms") or 20000), keyboard_steps=int(browser_cfg.get("keyboard_steps") or 24), axe_script_path=browser_cfg.get("axe_script_path"))
                    metrics += rows
                    add_source(sources, "browser", "Chromium/Playwright", "AVAILABLE", f"baseline requests={details['baseline']['request_count']}; accessibility manual review remains required; privacy legal interpretation remains separate")
            except Exception as exc:
                add_source(sources, "browser", "Chromium/Playwright", "UNAVAILABLE", str(exc))

        payload = bundle(target_url, mode, sources, metrics)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: enrichment mode={mode} sources={len(sources)} metrics={len(metrics)}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
