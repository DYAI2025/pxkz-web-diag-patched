#!/usr/bin/env python3
"""End-to-end regression for the Pixelkiez visualization/reporting architecture v1."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(args: list[str], expect: int = 0, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != expect:
        raise AssertionError(
            f"return code {proc.returncode} != {expect}: {' '.join(args)}\n"
            f"STDOUT:\n{proc.stdout[-4000:]}\nSTDERR:\n{proc.stderr[-4000:]}"
        )
    return proc


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_visual_architecture_evals.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    py = sys.executable
    try:
        with tempfile.TemporaryDirectory(prefix="pxk-visual-architecture-") as td:
            t = Path(td)
            scored = t / "diagnosis-report-scored.json"
            out = t / "deliverables"
            run([py, str(root / "scripts/compute_score.py"), str(root / "evals/fixtures/synthetic-report.json"), str(scored)])
            run([py, str(root / "scripts/build_audit_deliverables.py"), str(scored), str(out), "--release-mode", "proof", "--force-svg-fallback"], timeout=300)

            required = [
                "diagnosis-report.json", "analysis_report.json", "analysis_report.md",
                "client-report-model.json", "visualization-plan.json",
                "visualization-render-receipt.json", "customer_presentation.html",
                "presentation-render-receipt.json", "customer_presentation.pdf",
                "customer_presentation.visual-qa.json", "customer_presentation.semantic-qa.json",
                "customer-presentation-quality-report.json",
                "deliverable-manifest.json", "deliverable-bundle-validation.json",
            ]
            missing = [name for name in required if not (out / name).is_file()]
            if missing:
                raise AssertionError(f"missing deliverables: {missing}")

            analysis = json.loads((out / "analysis_report.json").read_text(encoding="utf-8"))
            canonical = json.loads(scored.read_text(encoding="utf-8"))
            if len(analysis.get("metrics", [])) != len(canonical.get("metrics", [])):
                raise AssertionError("internal report metric count mismatch")
            if analysis.get("sources") != canonical.get("sources"):
                raise AssertionError("internal report source register mismatch")
            markdown = (out / "analysis_report.md").read_text(encoding="utf-8")
            for metric in canonical.get("metrics", []):
                mid = str(metric.get("id"))
                if markdown.count(f'<a id="metric-{mid.lower()}"></a>') != 1:
                    raise AssertionError(f"metric anchor missing/duplicate: {mid}")

            plan = json.loads((out / "visualization-plan.json").read_text(encoding="utf-8"))
            selected = [v for v in plan.get("visuals", []) if v.get("status") == "SELECTED"]
            if not 5 <= len(selected) <= 7:
                raise AssertionError(f"full fixture expected 5-7 selected visuals, got {len(selected)}")
            if len(plan.get("top_levers", [])) != 4:
                raise AssertionError("exactly four levers are required")
            selected_ids = {v.get("template_id") for v in selected}
            for required_id in {"V02_CATEGORY_BARS", "V03_TOP_LEVERS"}:
                if required_id not in selected_ids:
                    raise AssertionError(f"required core visual absent: {required_id}")
            for forbidden in {"V01_OVERALL_SCORE", "V11_SEVERITY_DISTRIBUTION", "V12_AUDIT_COVERAGE"}:
                if forbidden in selected_ids:
                    raise AssertionError(f"internal/redundant customer visual selected: {forbidden}")
            for forbidden in {"V04_FINDABILITY_BENCHMARK", "V05_RANKING_POSITION"}:
                if forbidden in selected_ids:
                    raise AssertionError(f"benchmark/ranking selected without benchmark_data: {forbidden}")
            excluded = {x.get("template_id"): x.get("reason") for x in plan.get("excluded_candidates", [])}
            if excluded.get("V04_FINDABILITY_BENCHMARK") != "BENCHMARK_CONTEXT_MISSING":
                raise AssertionError("missing benchmark must be explicit")
            if excluded.get("V05_RANKING_POSITION") != "SERP_QUERY_CONTEXT_MISSING":
                raise AssertionError("missing ranking context must be explicit")

            visual_receipt = json.loads((out / "visualization-render-receipt.json").read_text(encoding="utf-8"))
            if visual_receipt.get("rendered_count") != len(selected):
                raise AssertionError("rendered visual count mismatch")
            if {x.get("backend") for x in visual_receipt.get("visuals", [])} != {"PIXELKIEZ_SVG_FALLBACK"}:
                raise AssertionError("forced fallback backend was not used truthfully")
            if visual_receipt.get("capabilities", {}).get("network_install_attempted") is not False:
                raise AssertionError("renderer attempted network installation")

            presentation = json.loads((out / "presentation-render-receipt.json").read_text(encoding="utf-8"))
            if presentation.get("renderer") != "WEASYPRINT":
                raise AssertionError("customer PDF must use WeasyPrint")
            if presentation.get("embedded_visual_count") != len(selected):
                raise AssertionError("not all selected visuals were embedded")
            if presentation.get("minimum_rendered_text_size_pt", 0) < 8.49:
                raise AssertionError("rendered text below 8.5 pt")
            if presentation.get("legacy_reportlab_default") is not False:
                raise AssertionError("legacy ReportLab must not be the default customer renderer")

            visual_qa = json.loads((out / "customer_presentation.visual-qa.json").read_text(encoding="utf-8"))
            if visual_qa.get("inspection_status") != "PENDING" or len(visual_qa.get("chart_pages", [])) != len(selected):
                raise AssertionError("visual QA must be pending and enumerate every chart page")
            semantic_qa = json.loads((out / "customer_presentation.semantic-qa.json").read_text(encoding="utf-8"))
            if semantic_qa.get("inspection_status") != "PENDING":
                raise AssertionError("semantic QA must not self-certify")
            quality = json.loads((out / "customer-presentation-quality-report.json").read_text(encoding="utf-8"))
            if quality.get("quality_status") != "PENDING_QA":
                raise AssertionError("first rendered PDF must remain quality PENDING_QA until actual inspection")
            bundle = json.loads((out / "deliverable-bundle-validation.json").read_text(encoding="utf-8"))
            if bundle.get("build_complete") is not True or bundle.get("customer_release_ready") is not False:
                raise AssertionError("proof build must be complete but not customer-release-ready before QA/exact fonts")

            # Core derived artifacts must be deterministic for the same frozen input.
            repeat_dir = t / "repeat"
            repeat_dir.mkdir()
            repeat_plan = repeat_dir / "visualization-plan.json"
            repeat_model = repeat_dir / "client-report-model.json"
            run([py, str(root / "scripts/build_visualization_plan.py"), str(scored), str(repeat_plan)])
            run([py, str(root / "scripts/build_client_report_model.py"), str(scored), str(repeat_model), "--visual-plan", str(repeat_plan)])
            if sha(repeat_plan) != sha(out / "visualization-plan.json"):
                raise AssertionError("visualization plan is not deterministic")
            if sha(repeat_model) != sha(out / "client-report-model.json"):
                raise AssertionError("client model is not deterministic")

            # Exact font policy is fail-closed when the runtime lacks either requested family.
            font = json.loads(run([py, str(root / "scripts/check_brand_fonts.py"), str(root), "--json"]).stdout)
            exact = bool(font.get("exact", {}).get("display") and font.get("exact", {}).get("data"))
            strict = subprocess.run([py, str(root / "scripts/check_brand_fonts.py"), str(root), "--require-exact"], text=True, capture_output=True)
            if exact and strict.returncode != 0:
                raise AssertionError("exact fonts found but strict font gate failed")
            if not exact and (strict.returncode == 0 or "BRAND_FONT_EXACT_REQUIRED" not in strict.stderr):
                raise AssertionError("missing exact fonts did not fail closed")

            # Unsafe SVG payloads are rejected by the visual asset validator.
            bad_receipt = json.loads((out / "visualization-render-receipt.json").read_text(encoding="utf-8"))
            first = bad_receipt["visuals"][0]
            bad_svg = out / first["svg_path"]
            original = bad_svg.read_text(encoding="utf-8")
            bad_svg.write_text(original.replace("</svg>", '<script>alert(1)</script></svg>'), encoding="utf-8")
            first["svg_sha256"] = sha(bad_svg)
            bad_receipt_path = out / "unsafe-receipt.json"
            bad_receipt_path.write_text(json.dumps(bad_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            unsafe = subprocess.run([py, str(root / "scripts/validate_visual_assets.py"), str(out / "visualization-plan.json"), str(bad_receipt_path), str(out / "visuals")], text=True, capture_output=True)
            if unsafe.returncode == 0 or "unsafe SVG element" not in unsafe.stderr:
                raise AssertionError("unsafe SVG script was not rejected")

        report = {
            "status": "PASS",
            "suite": "visualization-reporting-architecture",
            "mandatory_product_outputs": ["analysis_report.json", "analysis_report.md", "customer_presentation.pdf"],
            "metric_count": len(analysis.get("metrics", [])),
            "selected_visual_count": len(selected),
            "selected_template_ids": sorted(selected_ids),
            "top_lever_count": len(plan.get("top_levers", [])),
            "renderer": presentation.get("renderer"),
            "brand_font_status": presentation.get("brand_font_status"),
            "visual_qa_initial_status": visual_qa.get("inspection_status"),
            "semantic_qa_initial_status": semantic_qa.get("inspection_status"),
            "quality_gate_initial_status": quality.get("quality_status"),
            "customer_release_ready_before_qa": bundle.get("customer_release_ready"),
            "benchmark_without_context": "BLOCKED",
            "ranking_without_context": "BLOCKED",
            "unsafe_svg": "REJECTED",
            "does_not_prove": ["exact Schibsted availability", "live benchmark data", "customer approval", "commercial outcome"],
        }
        (root / "reports/visual-reporting-eval-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("PASS: visual/reporting architecture E2E (3 outputs, 5-7 visuals, WeasyPrint, no fake benchmarks, fail-closed fonts/QA/SVG)")
        return 0
    except Exception as exc:
        report = {"status": "FAIL", "suite": "visualization-reporting-architecture", "error": str(exc)}
        (root / "reports/visual-reporting-eval-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
