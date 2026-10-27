#!/usr/bin/env python3
"""Validate a completed page-by-page Pixelkiez PDF visual-QA manifest.

This validator checks completeness and artifact binding. It does not itself see the pages;
truthfulness of the visual inspection remains the responsibility of the declared inspector.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

GENERIC_CHECKS = {
    "text_readable",
    "plain_language_clear",
    "no_clipping",
    "no_overlap",
    "no_broken_glyphs",
    "customer_density_ok",
}
COVER_CHECKS = {"full_takeaway_visible","score_projection_visible_when_required","no_cross_page_sentence_split"}
CHART_CHECKS = {
    "finding_title_clear",
    "chart_labels_legible",
    "business_message_clear",
    "threshold_or_reference_clear_when_applicable",
    "no_internal_method_or_evidence_boilerplate",
}
ALLOWED_METHODS = {"agent_vision", "human_review", "hybrid"}


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return fail("usage: validate_pdf_visual_qa.py <input.pdf> <visual-qa.json>")
    pdf = Path(argv[1]).resolve()
    qa = Path(argv[2]).resolve()
    if not pdf.is_file() or not qa.is_file():
        return fail("PDF or visual-QA report missing")
    try:
        data = json.loads(qa.read_text(encoding="utf-8"))
        reader = PdfReader(str(pdf))
    except Exception as exc:
        return fail(str(exc))
    if data.get("schema_version") not in {"1.0", "1.1", "1.2"}:
        return fail("visual-QA schema_version must be 1.0, 1.1 or 1.2")
    if data.get("pdf_sha256") != digest(pdf):
        return fail("visual-QA report is not bound to this PDF digest")
    if data.get("page_count") != len(reader.pages):
        return fail("visual-QA page_count does not match PDF")
    if data.get("inspection_status") != "PASS":
        return fail("inspection_status must be PASS after actual visual inspection")
    if data.get("inspection_method") not in ALLOWED_METHODS:
        return fail("inspection_method must be agent_vision, human_review, or hybrid")
    if not str(data.get("inspected_by") or "").strip():
        return fail("inspected_by is required")
    if data.get("schema_version") == "1.2":
        cover = data.get("cover_checks")
        if not isinstance(cover, dict) or not COVER_CHECKS.issubset(cover):
            return fail("cover-specific visual checks incomplete")
        failed_cover = [key for key in COVER_CHECKS if cover.get(key) is not True]
        if failed_cover:
            return fail("cover-specific visual checks failed: " + ", ".join(sorted(failed_cover)))
    pages = data.get("pages")
    if not isinstance(pages, list) or len(pages) != len(reader.pages):
        return fail("every PDF page must have one visual-QA page record")
    seen = set()
    for item in pages:
        if not isinstance(item, dict) or not isinstance(item.get("page"), int):
            return fail("invalid page record")
        n = item["page"]
        seen.add(n)
        image = Path(str(item.get("image", "")))
        if not image.is_absolute():
            image = (qa.parent / image).resolve()
        if not image.is_file():
            return fail(f"rendered image missing for page {n}: {image}")
        checks = item.get("checks")
        if not isinstance(checks, dict) or not GENERIC_CHECKS.issubset(checks):
            return fail(f"page {n} missing generic visual checks")
        failed = [key for key in GENERIC_CHECKS if checks.get(key) is not True]
        if failed:
            return fail(f"page {n} has incomplete/failed visual checks: {', '.join(sorted(failed))}")
    if seen != set(range(1, len(reader.pages) + 1)):
        return fail("visual-QA page numbering must cover every PDF page exactly once")
    chart_pages = data.get("chart_pages")
    if not isinstance(chart_pages, list):
        return fail("chart_pages must be an array")
    actual_chart_pages = [idx for idx, page in enumerate(reader.pages, 1) if "WEBSITE-BEFUND" in re.sub(r"\s+", "", (page.extract_text() or "")).upper()]
    if not 4 <= len(actual_chart_pages) <= 7:
        return fail(f"customer PDF must contain 4-7 data-visual pages, got {len(actual_chart_pages)}")
    declared_chart_pages = [item.get("page") for item in chart_pages if isinstance(item, dict)]
    if declared_chart_pages != actual_chart_pages:
        return fail(f"visual-QA chart page mapping mismatch declared={declared_chart_pages} actual={actual_chart_pages}")
    seen_chart_pages = set()
    for item in chart_pages:
        if not isinstance(item, dict) or not re.fullmatch(r"V(?:0[1-9]|1[0-4])_[A-Z0-9_]+", str(item.get("template_id") or "")):
            return fail("invalid chart page record")
        if item.get("page") in seen_chart_pages:
            return fail("duplicate chart page record")
        seen_chart_pages.add(item.get("page"))
        checks = item.get("checks")
        if not isinstance(checks, dict) or not CHART_CHECKS.issubset(checks):
            return fail(f"chart page {item.get('page')} missing chart-specific checks")
        failed = [key for key in CHART_CHECKS if checks.get(key) is not True]
        if failed:
            return fail(f"chart page {item.get('page')} has incomplete/failed checks: {', '.join(sorted(failed))}")
    print(f"PASS: visual QA bound to PDF ({len(reader.pages)} pages, {len(chart_pages)} chart pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
