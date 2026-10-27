#!/usr/bin/env python3
"""Regression-test the low-coverage, chart-led customer presentation path."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

FORBIDDEN = ["TECHNISCHER ANHANG", "QUELLEN & METHODEN", "MISSING / SOURCE_NEEDED", "not_assessed", "…"]


def run(args: list[str]) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError("command failed: " + " ".join(args))
    return result.stdout.strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_client_marketing_evals.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    fixture = root / "evals/fixtures/low-coverage-marketing-report.json"
    try:
        with tempfile.TemporaryDirectory(prefix="pxk-marketing-") as td:
            t = Path(td)
            scored = t / "scored.json"
            out = t / "deliverables"
            run([sys.executable, str(root / "scripts/compute_score.py"), str(fixture), str(scored)])
            score = json.loads(scored.read_text(encoding="utf-8"))["score_summary"]
            if score.get("coverage_percent") != 40 or score.get("score") is not None or score.get("label") != "Score nicht belastbar":
                raise RuntimeError("regression fixture must reproduce 40% coverage with hidden overall score")
            expected = {
                "findability_seo": (57, 70), "performance_technology": (None, 0),
                "ux_conversion": (None, 10), "accessibility": (None, 35),
                "trust_privacy_content": (52, 60), "ai_readiness": (62, 85),
            }
            cats = {c["category"]: (c.get("score"), c.get("coverage_percent")) for c in score.get("category_scores", [])}
            if cats != expected:
                raise RuntimeError(f"unexpected category regression state: {cats}")

            out.mkdir(parents=True, exist_ok=True)
            canonical = out / "diagnosis-report.json"
            canonical.write_bytes(scored.read_bytes())
            analysis_path = out / "analysis_report.json"
            plan_path = out / "visualization-plan.json"
            model_path = out / "client-report-model.json"
            visuals = out / "visuals"
            vreceipt = out / "visualization-render-receipt.json"
            pdf_path = out / "customer_presentation.pdf"
            receipt_path = out / "presentation-render-receipt.json"
            run([sys.executable, str(root / "scripts/build_internal_analysis_report.py"), str(canonical), str(analysis_path)])
            run([sys.executable, str(root / "scripts/build_visualization_plan.py"), str(canonical), str(plan_path)])
            run([sys.executable, str(root / "scripts/build_client_report_model.py"), str(canonical), str(model_path), "--visual-plan", str(plan_path)])
            run([sys.executable, str(root / "scripts/render_visualizations.py"), str(plan_path), str(visuals), "--receipt", str(vreceipt), "--force-fallback"])
            run([sys.executable, str(root / "scripts/render_diagnosis_pdf.py"), str(model_path), str(pdf_path), "--visual-plan", str(plan_path), "--visual-receipt", str(vreceipt), "--visual-dir", str(visuals), "--render-receipt", str(receipt_path), "--html-out", str(out / "customer_presentation.html")])
            run([sys.executable, str(root / "scripts/validate_pdf_output.py"), str(pdf_path), str(model_path)])
            model = json.loads(model_path.read_text(encoding="utf-8"))
            if len(model.get("findings", [])) != 4:
                raise RuntimeError("customer story must contain exactly four levers")
            if model.get("client_story", {}).get("technical_appendix_rendered") is not False:
                raise RuntimeError("technical appendix must be disabled for customer output")
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            if len(analysis.get("metrics", [])) < 40:
                raise RuntimeError("complete internal metric trace must remain in analysis_report.json")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            selected = [v for v in plan.get("visuals", []) if v.get("status") == "SELECTED"]
            if len(selected) < 4:
                raise RuntimeError(f"low-coverage customer report still requires >=4 truthful visuals, got {len(selected)}")
            if any(v.get("template_id") in {"V04_FINDABILITY_BENCHMARK", "V05_RANKING_POSITION"} for v in selected):
                raise RuntimeError("benchmark/ranking chart appeared without complete context")

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            reader = PdfReader(str(pdf_path))
            expected_pages = 5 + receipt.get("embedded_visual_count", 0)
            if len(reader.pages) != expected_pages or not 8 <= len(reader.pages) <= 12:
                raise RuntimeError(f"customer page budget failed: {len(reader.pages)} pages")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            hits = [marker for marker in FORBIDDEN if marker.casefold() in text.casefold()]
            if hits:
                raise RuntimeError("internal/truncated material leaked into customer PDF: " + ", ".join(hits))
            compact = re.sub(r"\s+", "", text).casefold()
            if "beweistnicht:" in compact:
                raise RuntimeError("internal evidence-boundary boilerplate leaked into customer PDF")
            run([sys.executable, str(root / "scripts/validate_customer_output_guardrails.py"), str(model_path), str(out / "customer_presentation.html"), str(pdf_path), str(visuals)])
        print("PASS: low-coverage regression -> hidden score, >=4 evidence visuals, four levers, complete internal report")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
