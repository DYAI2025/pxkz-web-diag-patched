#!/usr/bin/env python3
"""Exercise full, partial and hidden-score coverage gates using the synthetic registry-complete fixture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode:
        if result.stdout:
            print(result.stdout.strip(), file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError("command failed: " + " ".join(cmd))


def suppress_category(report: dict, category: str, metric_category: dict[str, str]) -> None:
    for metric in report.get("metrics", []):
        if metric_category.get(str(metric.get("id"))) != category or metric.get("applicable") is not True:
            continue
        metric["measurement_class"] = "not_assessed"
        metric["status"] = "not_assessed"
        metric["score"] = None
        metric["confidence"] = 1
        metric["source_or_method"] = "Score-gate eval: intentionally unassessed"
        metric["threshold_source"] = None
        metric["does_not_prove"] = "Deliberately unassessed in deterministic score-gate evaluation."


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_score_gate_evals.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    fixture = json.loads((root / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
    registry = json.loads((root / "assets/measurement-registry.json").read_text(encoding="utf-8"))
    metric_category = {m["id"]: m["category"] for m in registry["metrics"]}
    cases = [
        ("full", [], "FULL_SCORE", "Pixelkiez Score", True),
        ("partial", ["ux_conversion"], "PARTIAL_SCORE", "Pixelkiez Teilscore", True),
        ("hidden", ["findability_seo", "performance_technology", "ux_conversion"], "NO_SCORE", "Score nicht belastbar", False),
    ]
    with tempfile.TemporaryDirectory(prefix="pixelkiez-score-gates-") as tmp:
        tmpdir = Path(tmp)
        for name, categories, expected_status, expected_label, has_score in cases:
            report = deepcopy(fixture)
            for category in categories:
                suppress_category(report, category, metric_category)
            source = tmpdir / f"{name}.json"
            scored = tmpdir / f"{name}-scored.json"
            model = tmpdir / f"{name}-client.json"
            source.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            run([sys.executable, str(root / "scripts/compute_score.py"), str(source), str(scored)])
            data = json.loads(scored.read_text(encoding="utf-8"))
            summary = data["score_summary"]
            if summary["display_status"] != expected_status or summary["label"] != expected_label:
                raise RuntimeError(f"{name}: unexpected score gate {summary}")
            if (summary["score"] is not None) != has_score:
                raise RuntimeError(f"{name}: score visibility mismatch")
            run([sys.executable, str(root / "scripts/validate_report_input.py"), str(scored)])
            run([sys.executable, str(root / "scripts/build_client_report_model.py"), str(scored), str(model)])
            run([sys.executable, str(root / "scripts/validate_client_report_model.py"), str(model)])
            print(f"PASS: {name} coverage={summary['coverage_percent']} status={summary['display_status']} label={summary['label']}")
    print("PASS: score coverage gates")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
