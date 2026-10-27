#!/usr/bin/env python3
"""Public browser-state measurements for Pixelkiez accessibility/privacy enrichment."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from measurement_enrichment import metric_record, now_iso

ACCEPT_RE = re.compile(r"(?:alle\s+)?(?:akzeptieren|zustimmen)|accept(?:\s+all)?|allow(?:\s+all)?", re.I)
REJECT_RE = re.compile(r"(?:alle\s+)?ablehnen|nur\s+notwendige|reject(?:\s+all)?|decline", re.I)


def _chromium_path() -> str | None:
    explicit = os.getenv("PIXELKIEZ_CHROMIUM_PATH")
    if explicit and Path(explicit).is_file():
        return explicit
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _third_party(request_urls: list[str], target_url: str) -> list[str]:
    target = _host(target_url)
    hosts = []
    for u in request_urls:
        h = _host(u)
        if h and target and h != target and not h.endswith("." + target):
            hosts.append(h)
    return sorted(set(hosts))


def _storage_counts(page: Any) -> dict[str, int]:
    return page.evaluate("""() => ({local: localStorage.length, session: sessionStorage.length})""")


def _dom_accessibility_snapshot(page: Any) -> dict[str, Any]:
    return page.evaluate("""() => {
      const visible = el => {
        const s = getComputedStyle(el); const r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
      };
      const controls = [...document.querySelectorAll('button,input,select,textarea,a[href],[role="button"]')].filter(visible);
      const name = el => {
        const aria = (el.getAttribute('aria-label') || '').trim(); if (aria) return aria;
        const labelled = (el.getAttribute('aria-labelledby') || '').trim();
        if (labelled) { const t = labelled.split(/\\s+/).map(id => document.getElementById(id)?.innerText || '').join(' ').trim(); if (t) return t; }
        if (el.id) { const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (lab?.innerText?.trim()) return lab.innerText.trim(); }
        if (el.closest('label')?.innerText?.trim()) return el.closest('label').innerText.trim();
        const text = (el.innerText || el.value || el.getAttribute('title') || el.getAttribute('alt') || '').trim();
        return text;
      };
      const unnamed = controls.filter(el => !name(el)).map(el => ({tag: el.tagName.toLowerCase(), type: el.getAttribute('type'), id: el.id || null}));
      const missingAlt = [...document.querySelectorAll('img:not([alt])')].filter(visible).length;
      return {interactive_count: controls.length, unnamed_controls: unnamed.slice(0,50), unnamed_count: unnamed.length, images_missing_alt_attribute: missingAlt};
    }""")


def _keyboard_sample(page: Any, steps: int = 24) -> list[str]:
    seen: list[str] = []
    for _ in range(max(1, min(int(steps), 60))):
        page.keyboard.press("Tab")
        desc = page.evaluate("""() => { const e=document.activeElement; if(!e) return ''; return [e.tagName.toLowerCase(), e.id || '', e.getAttribute('name') || '', e.getAttribute('aria-label') || '', (e.innerText || '').trim().slice(0,60)].join('|'); }""")
        if desc and desc not in seen:
            seen.append(desc)
    return seen


def _find_consent_control(page: Any, pattern: re.Pattern[str]) -> Any | None:
    for selector in ("button", "[role=button]", "a"):
        loc = page.locator(selector)
        try:
            count = min(loc.count(), 80)
        except Exception:
            continue
        for i in range(count):
            item = loc.nth(i)
            try:
                if not item.is_visible():
                    continue
                txt = (item.inner_text(timeout=500) or "").strip()
            except Exception:
                continue
            if txt and pattern.search(txt):
                return item
    return None


def _capture_state(browser: Any, target_url: str, state: str, *, wait_ms: int, timeout_ms: int, keyboard_steps: int) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    request_urls: list[str] = []
    page.on("request", lambda req: request_urls.append(req.url))
    response_status = None
    action_found = False
    action_clicked = False
    try:
        response = page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
        response_status = response.status if response else None
        page.wait_for_timeout(wait_ms)
        if state in {"accept", "reject"}:
            control = _find_consent_control(page, ACCEPT_RE if state == "accept" else REJECT_RE)
            action_found = control is not None
            if control is not None:
                try:
                    control.click(timeout=2000)
                    action_clicked = True
                    page.wait_for_timeout(wait_ms)
                except Exception:
                    pass
        cookies = context.cookies()
        storage = _storage_counts(page)
        dom = _dom_accessibility_snapshot(page)
        focus = _keyboard_sample(page, keyboard_steps) if state == "baseline" else []
        overflow = page.evaluate("() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
        return {
            "state": state,
            "response_status": response_status,
            "request_count": len(request_urls),
            "third_party_hosts": _third_party(request_urls, target_url),
            "cookie_count": len(cookies),
            "cookie_names": sorted({str(c.get('name')) for c in cookies if c.get('name')})[:50],
            "storage": storage,
            "consent_control_found": action_found,
            "consent_control_clicked": action_clicked,
            "dom": dom,
            "keyboard_focus_targets": focus,
            "horizontal_overflow_px": int(overflow or 0),
        }
    finally:
        context.close()


def _axe_count(page: Any, axe_script_path: str) -> int:
    path = Path(axe_script_path)
    if not path.is_file():
        raise FileNotFoundError(f"axe script not found: {path}")
    page.add_script_tag(path=str(path))
    result = page.evaluate("""async () => await axe.run(document, {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22a','wcag22aa']}})""")
    violations = result.get("violations", []) if isinstance(result, dict) else []
    return sum(1 for v in violations if isinstance(v, dict) and str(v.get("impact")) in {"critical", "serious"})


def collect_browser_metrics(target_url: str, *, wait_ms: int = 800, timeout_ms: int = 20000, keyboard_steps: int = 24, axe_script_path: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"Playwright unavailable: {exc}") from exc
    chromium = _chromium_path()
    if not chromium:
        raise RuntimeError("no Chromium executable found; set PIXELKIEZ_CHROMIUM_PATH")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chromium, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            baseline = _capture_state(browser, target_url, "baseline", wait_ms=wait_ms, timeout_ms=timeout_ms, keyboard_steps=keyboard_steps)
            reject = _capture_state(browser, target_url, "reject", wait_ms=wait_ms, timeout_ms=timeout_ms, keyboard_steps=0)
            accept = _capture_state(browser, target_url, "accept", wait_ms=wait_ms, timeout_ms=timeout_ms, keyboard_steps=0)
            axe_count = None
            axe_error = None
            if axe_script_path:
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(wait_ms)
                    axe_count = _axe_count(page, axe_script_path)
                except Exception as exc:
                    axe_error = str(exc)
                finally:
                    context.close()
        finally:
            browser.close()
    observed_at = now_iso()
    dom = baseline["dom"]
    metrics = [
        metric_record("A11Y_UNNAMED_CONTROLS", status="MEASURED", value=int(dom.get("unnamed_count", 0)), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright DOM observation", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-a11y-unnamed", manual_review_required=True, context={"interactive_count": dom.get("interactive_count"), "sample": dom.get("unnamed_controls"), "images_missing_alt_attribute": dom.get("images_missing_alt_attribute")}),
        metric_record("A11Y_KEYBOARD_FOCUS_TARGETS", status="OBSERVED", value=len(baseline.get("keyboard_focus_targets", [])), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright keyboard sample", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-a11y-focus", manual_review_required=True, context={"sample": baseline.get("keyboard_focus_targets", [])}),
        metric_record("MOBILE_HORIZONTAL_OVERFLOW_PX", status="MEASURED", value=int(baseline.get("horizontal_overflow_px", 0)), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright mobile viewport", observed_at=observed_at, url=target_url, device="390x844", evidence_ref="BROWSER-mobile-overflow", manual_review_required=True, context={}),
        metric_record("PRIVACY_THIRD_PARTY_REQUESTS_PRECHOICE", status="MEASURED", value=len(baseline.get("third_party_hosts", [])), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright network observation", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-privacy-third-party", legal_review_required=True, context={"hosts": baseline.get("third_party_hosts", [])}),
        metric_record("PRIVACY_COOKIES_PRECHOICE", status="MEASURED", value=int(baseline.get("cookie_count", 0)), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright browser context", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-privacy-cookies", legal_review_required=True, context={"cookie_names": baseline.get("cookie_names", [])}),
        metric_record("PRIVACY_STORAGE_ITEMS_PRECHOICE", status="MEASURED", value=int((baseline.get("storage") or {}).get("local", 0)) + int((baseline.get("storage") or {}).get("session", 0)), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright storage observation", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-privacy-storage", legal_review_required=True, context={"storage": baseline.get("storage", {})}),
        metric_record("CONSENT_ACCEPT_CONTROL_FOUND", status="OBSERVED", value=bool(accept.get("consent_control_found")), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright visible control observation", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-consent-accept", legal_review_required=True, context={"clicked": accept.get("consent_control_clicked")}),
        metric_record("CONSENT_REJECT_CONTROL_FOUND", status="OBSERVED", value=bool(reject.get("consent_control_found")), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright visible control observation", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-consent-reject", legal_review_required=True, context={"clicked": reject.get("consent_control_clicked")}),
    ]
    if axe_count is not None:
        metrics.append(metric_record("A11Y_CRITICAL_SERIOUS_AUTOMATED", status="MEASURED", value=int(axe_count), source_type="PUBLIC_BROWSER", source_provider="Chromium/Playwright + supplied axe-core", observed_at=observed_at, url=target_url, evidence_ref="BROWSER-axe-critical-serious", manual_review_required=True, context={"axe_runtime": "supplied"}))
    details = {"chromium_path": chromium, "baseline": baseline, "reject": reject, "accept": accept, "axe_error": axe_error, "manual_accessibility_review_required": True, "privacy_legal_review_boundary": True}
    return metrics, details
