#!/usr/bin/env python3
"""Create a fail-closed visual-QA manifest for a rendered Pixelkiez PDF.

The manifest starts PENDING. Chart-page identity is taken from the canonical
visualization plan, not from customer-visible implementation markers. A vision-capable
agent or human must inspect every page and set the checks to true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

CHART_ID_RE = re.compile(r"\b(V(?:0[1-9]|1[0-4])_[A-Z0-9_]+)\b")
GENERIC_CHECKS = [
    "text_readable",
    "plain_language_clear",
    "no_clipping",
    "no_overlap",
    "no_broken_glyphs",
    "customer_density_ok",
]
COVER_CHECKS = [
    "full_takeaway_visible",
    "score_projection_visible_when_required",
    "no_cross_page_sentence_split",
]
CHART_CHECKS = [
    "finding_title_clear",
    "chart_labels_legible",
    "business_message_clear",
    "threshold_or_reference_clear_when_applicable",
    "no_internal_method_or_evidence_boilerplate",
]


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("rendered_dir")
    parser.add_argument("output")
    parser.add_argument("--visualization-plan")
    args = parser.parse_args(argv)
    pdf = Path(args.pdf).resolve()
    rendered = Path(args.rendered_dir).resolve()
    out = Path(args.output).resolve()
    plan_path = Path(args.visualization_plan).resolve() if args.visualization_plan else None
    if not pdf.is_file() or not rendered.is_dir():
        return fail("PDF or rendered directory missing")
    try:
        reader = PdfReader(str(pdf))
        plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path else None
    except Exception as exc:
        return fail(str(exc))
    images = sorted(rendered.glob("page-*.png"))
    if len(images) != len(reader.pages):
        return fail(f"rendered page count {len(images)} != PDF page count {len(reader.pages)}")

    page_texts = [(page.extract_text() or "") for page in reader.pages]
    pages = [
        {
            "page": idx,
            "image": str(image.relative_to(out.parent)) if image.is_relative_to(out.parent) else image.name,
            "checks": {key: False for key in GENERIC_CHECKS},
            "notes": "",
        }
        for idx, image in enumerate(images, 1)
    ]
    chart_pages: list[dict[str, object]] = []
    plan_digest = None
    if plan_path:
        if not isinstance(plan, dict) or not isinstance(plan.get("visuals"), list):
            return fail("visualization plan must contain visuals")
        selected = [item for item in plan["visuals"] if isinstance(item, dict) and item.get("status") == "SELECTED"]
        if not 4 <= len(selected) <= 7:
            return fail(f"visualization plan must select 4-7 customer visuals, got {len(selected)}")
        plan_digest = sha256(plan_path)
        for offset, item in enumerate(selected, start=3):
            if offset > len(page_texts):
                return fail("visualization plan exceeds PDF page count")
            template_id = str(item.get("template_id") or "")
            if not re.fullmatch(r"V(?:0[1-9]|1[0-4])_[A-Z0-9_]+", template_id):
                return fail(f"invalid selected customer chart template: {template_id}")
            normalized = re.sub(r"\s+", "", page_texts[offset - 1]).upper()
            if "WEBSITE-BEFUND" not in normalized:
                return fail(f"PDF page {offset} does not match planned customer visual anatomy")
            if "BEWEISTNICHT" in normalized or "DATENVISUAL" in normalized:
                return fail(f"PDF page {offset} leaks internal visual-method boilerplate")
            chart_pages.append({
                "page": offset,
                "template_id": template_id,
                "checks": {key: False for key in CHART_CHECKS},
                "notes": "",
            })
    else:
        # Legacy compatibility only. New customer builds always provide the plan.
        for idx, text in enumerate(page_texts, 1):
            normalized = re.sub(r"\s+", "", text).upper()
            id_text = re.sub(r"\s*_\s*", "_", text.upper())
            present = sorted(set(CHART_ID_RE.findall(id_text)))
            if present and "WEBSITE-BEFUND" in normalized and "BEWEISTNICHT" not in normalized:
                chart_pages.append({
                    "page": idx,
                    "template_id": present[0],
                    "checks": {key: False for key in CHART_CHECKS},
                    "notes": "",
                })

    manifest = {
        "schema_version": "1.2",
        "pdf_path": str(pdf.relative_to(out.parent)) if pdf.is_relative_to(out.parent) else pdf.name,
        "pdf_sha256": sha256(pdf),
        "visualization_plan_path": (str(plan_path.relative_to(out.parent)) if plan_path and plan_path.is_relative_to(out.parent) else (plan_path.name if plan_path else None)),
        "visualization_plan_sha256": plan_digest,
        "page_count": len(reader.pages),
        "inspection_status": "PENDING",
        "inspection_method": None,
        "inspected_by": None,
        "inspection_note": "Set PASS only after every rendered page and every planned chart page has actually been visually inspected.",
        "pages": pages,
        "cover_checks": {key: False for key in COVER_CHECKS},
        "chart_pages": chart_pages,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: created PENDING visual-QA manifest for {len(pages)} pages ({len(chart_pages)} planned chart pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
