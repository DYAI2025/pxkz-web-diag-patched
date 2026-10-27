#!/usr/bin/env python3
"""Validate legacy V01-V12 payload contracts through the explicit ReportLab rollback renderer."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: run_chart_template_evals.py <skill-dir>")
    root = Path(argv[1]).resolve()
    sys.path.insert(0, str(root / "scripts"))
    from chart_contract import validate_visualizations
    import render_diagnosis_pdf_reportlab_legacy as renderer

    fixture = json.loads((root / "evals" / "fixtures" / "chart-library-all-templates.json").read_text(encoding="utf-8"))
    charts = fixture.get("visualizations", [])
    errors = validate_visualizations(charts)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if {v.get("template_id") for v in charts if isinstance(v, dict)} != {f"V{i:02d}" for i in range(1, 13)}:
        return fail("fixture must cover V01-V12 exactly")

    model = {
        "meta": {"customer": "Internal chart contract smoke", "date": "27.08.2026"},
        "visualizations": charts,
    }
    brand = renderer.load(root / "assets" / "brand.json")
    with tempfile.TemporaryDirectory(prefix="pxk-chart-smoke-") as td:
        pdf = Path(td) / "all-templates-internal.pdf"
        canvas = Canvas(str(pdf), pagesize=(renderer.PAGE_W, renderer.PAGE_H))
        next_page = renderer.draw_visualizations(canvas, model, brand, 1)
        canvas.save()
        reader = PdfReader(str(pdf))
        if len(reader.pages) != 12 or next_page != 13:
            return fail(f"expected 12 internal chart pages, got {len(reader.pages)}")
        text = "\n".join((page.extract_text() or "") for page in reader.pages).casefold()
        for template_id in [f"V{i:02d}" for i in range(1, 13)]:
            if template_id.casefold() not in text:
                return fail(f"rendered template marker missing: {template_id}")
        if "beweist nicht" not in text:
            return fail("internal chart smoke PDF lacks limitation blocks")
    print("PASS: V01-V12 payload contracts and internal renderer smoke; V12 remains internal-only for customer default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
