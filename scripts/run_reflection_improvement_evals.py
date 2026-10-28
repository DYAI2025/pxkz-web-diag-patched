#!/usr/bin/env python3
"""Regression-test prior Baumdienst quality failures against the current chart-led architecture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


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

            # V11 (finding count) is internal-only, which leaves three admissible customer visuals: the customer
            # presentation stays blocked until a real fourth visual exists (SEM-003). The build is atomic.
            blocked = subprocess.run([sys.executable, str(root / "scripts/build_audit_deliverables.py"), str(scored), str(out), "--force-svg-fallback"],
                                     text=True, capture_output=True)
            if blocked.returncode == 0 or "CUSTOMER_MIN_VISUALS_NOT_MET" not in (blocked.stdout + blocked.stderr):
                raise RuntimeError("Baumdienst customer bundle must fail closed below four admissible visuals")
            if (out / "customer_presentation.pdf").exists() or (out / "visualization-plan.json").exists():
                raise RuntimeError("blocked Baumdienst build left customer artifacts behind")
            run([sys.executable, str(root / "scripts/build_internal_analysis_report.py"), str(scored), str(t / "analysis_report.json")])
            analysis = json.loads((t / "analysis_report.json").read_text(encoding="utf-8"))
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
        print("PASS: reflection regression -> labelled partial score, customer bundle fails closed below four admissible visuals, full internal report, voice handoff")
        return 0
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
