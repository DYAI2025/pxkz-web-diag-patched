#!/usr/bin/env python3
"""Regression-test prior Baumdienst quality failures against the current chart-led architecture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from pypdf import PdfReader


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError("command failed: " + " ".join(cmd))


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        print("FAIL: usage: run_reflection_improvement_evals.py <website-skill-dir> [voice-skill-dir]", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    fixture = root / "evals/fixtures/baumdienst-renner-reflection-regression.json"
    try:
        with tempfile.TemporaryDirectory(prefix="pxk-reflect-") as td:
            t = Path(td)
            scored = t / "scored.json"
            out = t / "deliverables"
            packet = t / "website-audit-packet.json"
            csv_path = t / "batch.csv"
            val = t / "batch.validation.json"
            run([sys.executable, str(root / "scripts/compute_score.py"), str(fixture), str(scored)])
            score = json.loads(scored.read_text(encoding="utf-8"))["score_summary"]
            if score.get("coverage_percent") != 56 or score.get("score") != 71 or score.get("display_status") != "PARTIAL_SCORE" or score.get("label") != "Pixelkiez Teilscore":
                raise RuntimeError("Baumdienst regression must expose a clearly labelled 56% partial score, not a full score")

            run([sys.executable, str(root / "scripts/build_audit_deliverables.py"), str(scored), str(out), "--force-svg-fallback"])
            model = json.loads((out / "client-report-model.json").read_text(encoding="utf-8"))
            story = model["client_story"]
            if not 4 <= story.get("real_chart_count", 0) <= 7:
                raise RuntimeError("client-model decision visual count must stay within the approved 4-7 range")
            if story.get("visualization_plan_is_canonical") is not True:
                raise RuntimeError("client model is not bound to the canonical external visualization plan")
            plan = json.loads((out / "visualization-plan.json").read_text(encoding="utf-8"))
            selected = [v for v in plan.get("visuals", []) if v.get("status") == "SELECTED"]
            direct_count = sum(v.get("evidence_class") == "DIRECT" for v in selected)
            derived_count = sum(str(v.get("evidence_class", "")).startswith("DERIVED") for v in selected)
            if direct_count < 2:
                raise RuntimeError("expected at least two direct-evidence visuals in the canonical plan")
            if derived_count > 3:
                raise RuntimeError("derived overview visuals overused")
            if len(selected) < 4:
                raise RuntimeError("Baumdienst presentation must contain at least four approved visuals")
            if any(v.get("template_id") in {"V04_FINDABILITY_BENCHMARK", "V05_RANKING_POSITION"} for v in selected):
                raise RuntimeError("unsourced benchmark/ranking visual selected")
            receipt = json.loads((out / "presentation-render-receipt.json").read_text(encoding="utf-8"))
            if receipt.get("renderer") != "WEASYPRINT" or receipt.get("embedded_visual_count", 0) < 4:
                raise RuntimeError("Baumdienst PDF is not chart-led WeasyPrint output")
            text = "\n".join((p.extract_text() or "") for p in PdfReader(str(out / "customer_presentation.pdf")).pages)
            for bad in ["DERIVED", "NONE_OFFICIAL", "CATEGORY:", "…", "LCP", "CTA", "Canonical"]:
                if bad.casefold() in text.casefold():
                    raise RuntimeError("customer PDF leaked " + bad)
            analysis = json.loads((out / "analysis_report.json").read_text(encoding="utf-8"))
            if len(analysis.get("metrics", [])) != len(json.loads(scored.read_text(encoding="utf-8")).get("metrics", [])):
                raise RuntimeError("Baumdienst internal report lost metrics")

            run([sys.executable, str(root / "scripts/build_website_audit_packet.py"), str(scored), str(packet)])
            run([sys.executable, str(root / "scripts/validate_website_audit_packet.py"), str(packet)])
            packet_data = json.loads(packet.read_text(encoding="utf-8"))
            if packet_data["remediation_priorities"][0]["finding_id"] != "F-001":
                raise RuntimeError("remediation priority regression")
            if packet_data["conversation_hooks"][0]["finding_id"] != "F-001":
                raise RuntimeError("voice hook selector regression")
            run([sys.executable, str(root / "scripts/build_elevenlabs_batch_csv.py"), str(scored), str(csv_path), "--validation-out", str(val)])
            if len(argv) == 3:
                run([sys.executable, str(root / "scripts/validate_cross_skill_batch_contract.py"), str(Path(argv[2]).resolve())])
        print("PASS: reflection regression -> labelled partial score, >=4 visuals, readable brand PDF, full internal report, voice handoff")
        return 0
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
