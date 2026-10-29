#!/usr/bin/env python3
"""Regression-test the low-coverage customer path: hidden score, full internal report, fail-closed customer plan."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


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
            run([sys.executable, str(root / "scripts/build_internal_analysis_report.py"), str(canonical), str(analysis_path)])
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            if len(analysis.get("metrics", [])) < 40:
                raise RuntimeError("complete internal metric trace must remain in analysis_report.json")
            # Without the internal-only finding-count visual this case has three admissible customer visuals,
            # so the customer presentation must fail closed instead of padding the story (SEM-003).
            blocked = subprocess.run([sys.executable, str(root / "scripts/build_visualization_plan.py"), str(canonical), str(plan_path)],
                                     text=True, capture_output=True)
            if blocked.returncode == 0 or "CUSTOMER_MIN_VISUALS_NOT_MET" not in blocked.stderr:
                raise RuntimeError("low-coverage customer plan must fail closed below four admissible visuals: " + blocked.stderr.strip())
            if plan_path.exists():
                raise RuntimeError("blocked customer plan must not leave a plan artifact")
        print("PASS: low-coverage regression -> hidden score, complete internal report, customer presentation fails closed below four admissible visuals")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
