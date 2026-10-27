#!/usr/bin/env python3
"""Read-only HTTP adapters and deterministic parsers for Pixelkiez enrichment sources."""
from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from measurement_enrichment import metric_record, now_iso

ALLOWED_HOSTS = {
    "www.googleapis.com",
    "searchconsole.googleapis.com",
    "analyticsdata.googleapis.com",
    "chromeuxreport.googleapis.com",
    "api.dataforseo.com",
}


def _http_json(url: str, *, method: str = "GET", payload: Any = None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"blocked outbound host: {host}")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    merged = {"Accept": "application/json", "User-Agent": "PixelkiezWebsiteDiagnosis/measurement-enrichment"}
    if data is not None:
        merged["Content-Type"] = "application/json; charset=utf-8"
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8"))


def _basic_auth(login: str, password: str) -> str:
    token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def parse_pagespeed(payload: dict[str, Any], target_url: str, strategy: str, *, source_type: str = "PUBLIC_API", evidence_prefix: str = "PSI") -> list[dict[str, Any]]:
    lr = payload.get("lighthouseResult") if isinstance(payload, dict) else None
    if not isinstance(lr, dict):
        raise ValueError("PageSpeed response missing lighthouseResult")
    fetch_time = str(lr.get("fetchTime") or now_iso())
    cat = lr.get("categories", {}).get("performance", {}) if isinstance(lr.get("categories"), dict) else {}
    audits = lr.get("audits", {}) if isinstance(lr.get("audits"), dict) else {}
    records: list[dict[str, Any]] = []
    score = _float(cat.get("score"))
    if score is not None:
        records.append(metric_record("PSI_PERFORMANCE_SCORE", status="MEASURED", value=round(score * 100, 1), source_type=source_type, source_provider="Google PageSpeed Insights / Lighthouse", observed_at=fetch_time, url=target_url, device=strategy.upper(), evidence_ref=f"{evidence_prefix}-{strategy}-score", context={"strategy": strategy}))
    lcp = _float((audits.get("largest-contentful-paint") or {}).get("numericValue"))
    if lcp is not None:
        records.append(metric_record("PSI_LCP_LAB_MS", status="MEASURED", value=round(lcp, 1), source_type=source_type, source_provider="Google PageSpeed Insights / Lighthouse", observed_at=fetch_time, url=target_url, device=strategy.upper(), evidence_ref=f"{evidence_prefix}-{strategy}-lcp", context={"strategy": strategy}))
    cls = _float((audits.get("cumulative-layout-shift") or {}).get("numericValue"))
    if cls is not None:
        records.append(metric_record("PSI_CLS_LAB", status="MEASURED", value=round(cls, 4), source_type=source_type, source_provider="Google PageSpeed Insights / Lighthouse", observed_at=fetch_time, url=target_url, device=strategy.upper(), evidence_ref=f"{evidence_prefix}-{strategy}-cls", context={"strategy": strategy}))
    if not records:
        raise ValueError("PageSpeed response contained no supported performance metrics")
    return records


def fetch_pagespeed(target_url: str, api_key: str, strategy: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    query = urllib.parse.urlencode({"url": target_url, "strategy": strategy, "category": "performance", "key": api_key})
    payload = _http_json(f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?{query}")
    return payload, parse_pagespeed(payload, target_url, strategy)


def parse_crux(payload: dict[str, Any], target_url: str, form_factor: str, *, source_type: str = "PUBLIC_API", evidence_prefix: str = "CRUX") -> list[dict[str, Any]]:
    record = payload.get("record") if isinstance(payload, dict) else None
    if not isinstance(record, dict):
        raise ValueError("CrUX response missing record")
    collection = record.get("collectionPeriod") or {}
    observed_at = now_iso()
    date_range = None
    if isinstance(collection, dict) and collection.get("firstDate") and collection.get("lastDate"):
        def fmt(d: Any) -> str:
            if isinstance(d, dict):
                return f"{int(d.get('year',0)):04d}-{int(d.get('month',0)):02d}-{int(d.get('day',0)):02d}"
            return str(d)
        date_range = {"start": fmt(collection["firstDate"]), "end": fmt(collection["lastDate"])}
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
    mapping = {
        "largest_contentful_paint": ("CRUX_LCP_P75_MS", 1.0),
        "interaction_to_next_paint": ("CRUX_INP_P75_MS", 1.0),
        "cumulative_layout_shift": ("CRUX_CLS_P75", 1.0),
    }
    out: list[dict[str, Any]] = []
    for provider_key, (mid, factor) in mapping.items():
        raw = metrics.get(provider_key)
        if not isinstance(raw, dict):
            continue
        p75 = _float((raw.get("percentiles") or {}).get("p75"))
        if p75 is None:
            continue
        value = p75 * factor
        out.append(metric_record(mid, status="MEASURED", value=round(value, 4 if mid.endswith("P75") else 1), source_type=source_type, source_provider="Chrome UX Report API", observed_at=observed_at, date_range=date_range, url=target_url, device=form_factor, evidence_ref=f"{evidence_prefix}-{form_factor}-{provider_key}", context={"form_factor": form_factor, "record_key": record.get("key")}))
    if not out:
        raise ValueError("CrUX response contained no supported p75 metrics")
    return out


def fetch_crux(target_url: str, api_key: str, form_factor: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    query = urllib.parse.urlencode({"key": api_key})
    payload = _http_json(f"https://chromeuxreport.googleapis.com/v1/records:queryRecord?{query}", method="POST", payload={"url": target_url, "formFactor": form_factor, "metrics": ["largest_contentful_paint", "interaction_to_next_paint", "cumulative_layout_shift"]})
    return payload, parse_crux(payload, target_url, form_factor)


def parse_gsc_query(payload: dict[str, Any], target_url: str, query: str, start_date: str, end_date: str, *, location: str | None = None, device: str | None = None, source_type: str = "AUTHORIZED_API", evidence_prefix: str = "GSC") -> list[dict[str, Any]]:
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not rows:
        return []
    row = rows[0] if isinstance(rows[0], dict) else {}
    observed_at = now_iso()
    common = dict(source_type=source_type, source_provider="Google Search Console Search Analytics", observed_at=observed_at, date_range={"start": start_date, "end": end_date}, url=target_url, query=query, location=location, device=device, context={"row_count": len(rows)})
    out = []
    vals = [
        ("GSC_AVG_POSITION", row.get("position"), "position"),
        ("GSC_IMPRESSIONS", row.get("impressions"), "impressions"),
        ("GSC_CLICKS", row.get("clicks"), "clicks"),
        ("GSC_CTR", row.get("ctr"), "ctr"),
    ]
    for mid, raw, suffix in vals:
        val = _float(raw)
        if val is None:
            continue
        if mid in {"GSC_IMPRESSIONS", "GSC_CLICKS"}:
            val = int(round(val))
        else:
            val = round(val, 4)
        out.append(metric_record(mid, status="MEASURED", value=val, evidence_ref=f"{evidence_prefix}-{suffix}", **common))
    return out


def fetch_gsc_query(site_url: str, target_url: str, query: str, start_date: str, end_date: str, token: str, *, device: str | None = None, country: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    filters = [{"dimension": "query", "operator": "equals", "expression": query}]
    if device:
        filters.append({"dimension": "device", "operator": "equals", "expression": device})
    if country:
        filters.append({"dimension": "country", "operator": "equals", "expression": country})
    body = {"startDate": start_date, "endDate": end_date, "dimensions": ["query"], "dimensionFilterGroups": [{"filters": filters}], "rowLimit": 10, "dataState": "final"}
    encoded = urllib.parse.quote(site_url, safe="")
    payload = _http_json(f"https://www.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query", method="POST", payload=body, headers=_bearer(token))
    return payload, parse_gsc_query(payload, target_url, query, start_date, end_date, location=country, device=device)


def parse_gsc_inspection(payload: dict[str, Any], target_url: str, *, source_type: str = "AUTHORIZED_API", evidence_prefix: str = "GSC-INSPECT") -> list[dict[str, Any]]:
    result = payload.get("inspectionResult") if isinstance(payload, dict) else None
    idx = result.get("indexStatusResult") if isinstance(result, dict) else None
    if not isinstance(idx, dict):
        raise ValueError("URL Inspection response missing indexStatusResult")
    observed_at = now_iso()
    verdict = str(idx.get("verdict") or idx.get("coverageState") or "UNKNOWN")
    google_canonical = idx.get("googleCanonical")
    user_canonical = idx.get("userCanonical")
    align = "UNKNOWN"
    if google_canonical and user_canonical:
        align = "MATCH" if str(google_canonical).rstrip("/") == str(user_canonical).rstrip("/") else "MISMATCH"
    context = {k: idx.get(k) for k in ("coverageState", "robotsTxtState", "indexingState", "lastCrawlTime", "pageFetchState", "googleCanonical", "userCanonical", "crawledAs") if idx.get(k) is not None}
    return [
        metric_record("GSC_INDEX_VERDICT", status="OBSERVED", value=verdict, source_type=source_type, source_provider="Google Search Console URL Inspection", observed_at=observed_at, url=target_url, evidence_ref=f"{evidence_prefix}-verdict", context=context),
        metric_record("GSC_CANONICAL_ALIGNMENT", status="OBSERVED", value=align, source_type=source_type, source_provider="Google Search Console URL Inspection", observed_at=observed_at, url=target_url, evidence_ref=f"{evidence_prefix}-canonical", context=context),
    ]


def fetch_gsc_inspection(site_url: str, target_url: str, token: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body = {"inspectionUrl": target_url, "siteUrl": site_url, "languageCode": "de-DE"}
    payload = _http_json("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", method="POST", payload=body, headers=_bearer(token))
    return payload, parse_gsc_inspection(payload, target_url)


def _ga_metric_values(payload: dict[str, Any]) -> list[str]:
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not rows or not isinstance(rows[0], dict):
        return []
    return [str(x.get("value", "")) for x in rows[0].get("metricValues", []) if isinstance(x, dict)]


def parse_ga4_summary(payload: dict[str, Any], target_url: str, start_date: str, end_date: str, *, source_type: str = "AUTHORIZED_API", evidence_prefix: str = "GA4") -> list[dict[str, Any]]:
    values = _ga_metric_values(payload)
    if len(values) < 2:
        return []
    observed_at = now_iso()
    out = []
    for mid, raw, suffix in (("GA4_ACTIVE_USERS", values[0], "active-users"), ("GA4_SESSIONS", values[1], "sessions")):
        val = _float(raw)
        if val is not None:
            out.append(metric_record(mid, status="MEASURED", value=int(round(val)), source_type=source_type, source_provider="Google Analytics Data API", observed_at=observed_at, date_range={"start": start_date, "end": end_date}, url=target_url, evidence_ref=f"{evidence_prefix}-{suffix}", context={"sampling_metadata_present": bool((payload.get("metadata") or {}).get("samplingMetadatas"))}))
    return out


def fetch_ga4_summary(property_id: str, target_url: str, start_date: str, end_date: str, token: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body = {"dateRanges": [{"startDate": start_date, "endDate": end_date}], "metrics": [{"name": "activeUsers"}, {"name": "sessions"}]}
    payload = _http_json(f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport", method="POST", payload=body, headers=_bearer(token))
    return payload, parse_ga4_summary(payload, target_url, start_date, end_date)


EVENT_METRIC_IDS = {
    "primary_cta_click": "GA4_PRIMARY_CTA_CLICKS",
    "form_start": "GA4_FORM_STARTS",
    "form_submit": "GA4_FORM_SUBMITS",
    "phone_click": "GA4_PHONE_CLICKS",
}


def parse_ga4_event(payload: dict[str, Any], target_url: str, start_date: str, end_date: str, canonical_event: str, configured_event_name: str, *, source_type: str = "AUTHORIZED_API", evidence_prefix: str = "GA4-EVENT") -> list[dict[str, Any]]:
    if canonical_event not in EVENT_METRIC_IDS:
        raise ValueError(f"unsupported canonical GA4 event: {canonical_event}")
    values = _ga_metric_values(payload)
    value = _float(values[0]) if values else 0.0
    if value is None:
        return []
    return [metric_record(EVENT_METRIC_IDS[canonical_event], status="MEASURED", value=int(round(value)), source_type=source_type, source_provider="Google Analytics Data API", observed_at=now_iso(), date_range={"start": start_date, "end": end_date}, url=target_url, evidence_ref=f"{evidence_prefix}-{canonical_event}", context={"canonical_event": canonical_event, "configured_event_name": configured_event_name})]


def fetch_ga4_event(property_id: str, target_url: str, start_date: str, end_date: str, token: str, canonical_event: str, configured_event_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": configured_event_name, "caseSensitive": True}}},
    }
    payload = _http_json(f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport", method="POST", payload=body, headers=_bearer(token))
    return payload, parse_ga4_event(payload, target_url, start_date, end_date, canonical_event, configured_event_name)


def _host_matches(item_url: str, target_url: str) -> bool:
    def host(u: str) -> str:
        h = (urlparse(u).hostname or "").lower()
        return h[4:] if h.startswith("www.") else h
    a, b = host(item_url), host(target_url)
    return bool(a and b and (a == b or a.endswith("." + b) or b.endswith("." + a)))


def parse_dataforseo(payload: dict[str, Any], target_url: str, query: str, *, requested_location: str | None = None, requested_device: str | None = None, source_type: str = "PAID_SERP_API", evidence_prefix: str = "DFS") -> list[dict[str, Any]]:
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    if not tasks or not isinstance(tasks[0], dict):
        raise ValueError("DataForSEO response missing tasks")
    results = tasks[0].get("result", [])
    if not results or not isinstance(results[0], dict):
        return []
    result = results[0]
    items = result.get("items", []) if isinstance(result.get("items"), list) else []
    organic = [x for x in items if isinstance(x, dict) and x.get("type") == "organic" and _host_matches(str(x.get("url") or ""), target_url)]
    if not organic:
        return []
    item = sorted(organic, key=lambda x: (int(x.get("rank_group") or 10**9), int(x.get("rank_absolute") or 10**9)))[0]
    position = item.get("rank_group")
    if not isinstance(position, int):
        return []
    observed_at = str(result.get("datetime") or now_iso())
    location = str(result.get("location_code") or result.get("location_name") or requested_location or "") or None
    device = str(result.get("device") or requested_device or "") or None
    context = {"rank_group": item.get("rank_group"), "rank_absolute": item.get("rank_absolute"), "result_url": item.get("url"), "result_title": item.get("title"), "check_url": result.get("check_url")}
    out = [metric_record("SERP_CURRENT_POSITION", status="MEASURED", value=position, source_type=source_type, source_provider="DataForSEO Google Organic Live Advanced", observed_at=observed_at, url=str(item.get("url") or target_url), query=query, location=location, device=device, evidence_ref=f"{evidence_prefix}-position", context=context)]
    page = item.get("page")
    if isinstance(page, int) and page > 0:
        out.append(metric_record("SERP_CURRENT_PAGE", status="MEASURED", value=page, source_type=source_type, source_provider="DataForSEO Google Organic Live Advanced", observed_at=observed_at, url=str(item.get("url") or target_url), query=query, location=location, device=device, evidence_ref=f"{evidence_prefix}-page", context=context))
    return out


def fetch_dataforseo(target_url: str, query: str, login: str, password: str, *, location_code: int | None = None, location_name: str | None = None, language_code: str = "de", device: str = "desktop", os_name: str | None = None, depth: int = 100) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    task: dict[str, Any] = {"keyword": query, "language_code": language_code, "device": device, "depth": max(10, min(int(depth), 200))}
    if location_code is not None:
        task["location_code"] = int(location_code)
    elif location_name:
        task["location_name"] = location_name
    else:
        raise ValueError("DataForSEO query requires location_code or location_name")
    if os_name:
        task["os"] = os_name
    payload = _http_json("https://api.dataforseo.com/v3/serp/google/organic/live/advanced", method="POST", payload=[task], headers={"Authorization": _basic_auth(login, password)})
    return payload, parse_dataforseo(payload, target_url, query, requested_location=location_name or str(location_code or ""), requested_device=device)
