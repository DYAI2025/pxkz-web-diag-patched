#!/usr/bin/env python3
"""Regression tests for scan-first semantics integrated with the chart-led PDF architecture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(args: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, text=True, capture_output=True)
    if proc.returncode != expect:
        raise AssertionError(
            f"return code {proc.returncode} != {expect}: {' '.join(args)}\n"
            f"STDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
        )
    return proc


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_customer_semantic_evals.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    py = sys.executable
    try:
        with tempfile.TemporaryDirectory(prefix="pxk-semantic-") as td:
            t = Path(td)
            scored = t / "scored.json"
            modelp = t / "model.json"
            planp = t / "visualization-plan.json"
            run([py, str(root / "scripts/compute_score.py"), str(root / "evals/fixtures/synthetic-report.json"), str(scored)])
            run([py, str(root / "scripts/build_visualization_plan.py"), str(scored), str(planp)])
            run([py, str(root / "scripts/build_client_report_model.py"), str(scored), str(modelp), "--visual-plan", str(planp)])
            model = json.loads(modelp.read_text(encoding="utf-8"))
            assert model.get("executive", {}).get("takeaway", "").startswith(("Wichtigster Hebel:", "Stärkste Basis:")), "executive takeaway must be scan-first"
            assert len(model.get("recommendation", {}).get("reason", "")) <= 135, "recommendation reason must stay concise"
            client_story = model.get("client_story", {})
            assert client_story.get("visualization_plan_is_canonical") is True
            assert 4 <= client_story.get("real_chart_count", 0) <= 7
            assert client_story.get("target_real_charts") == "4-7"
            story = model.get("semantic_story")
            assert isinstance(story, dict) and story.get("status") == "PASS", "semantic_story PASS summary missing"
            by_id = {f.get("id"): f for f in model.get("findings", [])}
            perf = by_id.get("F-002")
            assert perf and perf.get("presentation_mode") == "NUMBER_FIRST", "measured performance finding must be NUMBER_FIRST"
            signal = perf.get("numeric_signal")
            assert isinstance(signal, dict) and signal.get("metric_ref") == "PERF-02", "PERF-02 numeric signal missing"
            assert signal.get("display_value") == "3,8 s", f"unexpected signal: {signal}"
            for finding in model.get("findings", []):
                assert finding.get("presentation_mode") in {"NUMBER_FIRST", "EVIDENCE_VISUAL", "SHORT_TEXT"}
                assert len(finding.get("headline", "")) <= 110
                assert len(finding.get("observation", "")) <= 130
                assert len(finding.get("impact", "")) <= 135
                assert len(finding.get("action", "")) <= 125
            run([py, str(root / "scripts/validate_client_semantics.py"), str(modelp)])

            # Generic agency copy must fail before PDF rendering.
            bad = json.loads(modelp.read_text(encoding="utf-8"))
            bad["findings"][0].update({
                "headline": "Optimierungspotenzial",
                "observation": "Hier besteht Optimierungspotenzial.",
                "impact": "Der Bereich könnte verbessert werden.",
                "action": "Diesen Bereich optimieren.",
            })
            badp = t / "generic.json"
            badp.write_text(json.dumps(bad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            run([py, str(root / "scripts/validate_client_semantics.py"), str(badp)], expect=1)

            # Component-level render proof: create the actual chart-led PDF and PENDING semantic QA
            # without re-running the slower atomic bundle harness (covered separately).
            out = t / "deliverables"
            out.mkdir(parents=True, exist_ok=True)
            canonical = out / "diagnosis-report.json"
            canonical.write_bytes(scored.read_bytes())
            out_plan = out / "visualization-plan.json"
            out_model = out / "client-report-model.json"
            visuals = out / "visuals"
            vreceipt = out / "visualization-render-receipt.json"
            pdf = out / "customer_presentation.pdf"
            html = out / "customer_presentation.html"
            preceipt_path = out / "presentation-render-receipt.json"
            run([py, str(root / "scripts/build_visualization_plan.py"), str(canonical), str(out_plan)])
            run([py, str(root / "scripts/build_client_report_model.py"), str(canonical), str(out_model), "--visual-plan", str(out_plan)])
            run([py, str(root / "scripts/render_visualizations.py"), str(out_plan), str(visuals), "--receipt", str(vreceipt), "--force-fallback"])
            run([py, str(root / "scripts/render_diagnosis_pdf.py"), str(out_model), str(pdf), "--visual-plan", str(out_plan), "--visual-receipt", str(vreceipt), "--visual-dir", str(visuals), "--render-receipt", str(preceipt_path), "--html-out", str(html)])
            run([py, str(root / "scripts/validate_pdf_output.py"), str(pdf), str(out_model)])
            preceipt = json.loads(preceipt_path.read_text(encoding="utf-8"))
            assert preceipt.get("embedded_visual_count", 0) >= 4
            assert preceipt.get("body_text_size_pt", 0) >= 12
            semqa = out / "customer_presentation.semantic-qa.json"
            run([py, str(root / "scripts/create_customer_semantic_qa_manifest.py"), str(pdf), str(out_model), str(canonical), str(semqa)])
            manifest = json.loads(semqa.read_text(encoding="utf-8"))
            assert manifest.get("inspection_status") == "PENDING"
            roles = [p.get("role") for p in manifest.get("pages", [])]
            assert roles and roles[0] == "cover" and roles[-1] == "closing", f"semantic QA page roles invalid: {roles}"
            assert len(set(roles)) >= 6, f"semantic QA page roles collapsed: {roles}"
            run([
                py, str(root / "scripts/validate_customer_semantic_qa.py"),
                str(pdf), str(out_model), str(canonical), str(semqa),
            ], expect=1)
        print("PASS: customer semantics -> proactive model gates, chart-led PDF, fail-closed rendered QA")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
