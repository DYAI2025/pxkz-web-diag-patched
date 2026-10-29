"""Plan, model and PDF must show the same four levers when a priority profile applies."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "evals" / "fixtures"
TIE = FIX / "branch-priority-tie-report.SYNTHETIC.json"
CONTEXT = FIX / "branch-priority-context.SYNTHETIC.json"
CATALOG = FIX / "branch-priority-catalog.SYNTHETIC.json"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True)


def priority_args(test_mode: bool = True) -> list[str]:
    args = ["--priority-context", str(CONTEXT), "--priority-catalog", str(CATALOG),
            "--priority-catalog-sha256", hashlib.sha256(CATALOG.read_bytes()).hexdigest()]
    return args + (["--priority-allow-synthetic"] if test_mode else [])


class PriorityPipelineTests(unittest.TestCase):
    def build(self, tmp: Path, report: Path, extra: list[str]) -> tuple[dict, dict, dict]:
        plan, model, decision = tmp / "plan.json", tmp / "model.json", tmp / "decision.json"
        p = run("scripts/build_visualization_plan.py", str(report), str(plan), *extra)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        m = run("scripts/build_client_report_model.py", str(report), str(model), "--visual-plan", str(plan),
                *extra, "--priority-decision-out", str(decision))
        self.assertEqual(m.returncode, 0, m.stdout + m.stderr)
        return (json.loads(plan.read_text()), json.loads(model.read_text()), json.loads(decision.read_text()))

    def enriched_tie(self, tmp: Path) -> Path:
        """Tie report with the offline search/visitor enrichment: under the profile F-002 is no lever, so its threshold
        page is not admitted (owner decision 2026-10-29) and the bare tie report has only three visuals."""
        scored, enrichment, enriched = tmp / "tie.scored.json", tmp / "enrichment.json", tmp / "tie.enriched.json"
        for args in (("scripts/compute_score.py", str(TIE), str(scored)),
                     ("scripts/collect_measurement_enrichment.py", "https://example.com", str(enrichment), "--config",
                      str(FIX / "measurement-enrichment-config.json"), "--fixture-bundle", str(FIX / "measurement-provider-responses.json"), "--offline"),
                     ("scripts/attach_measurement_enrichment.py", str(scored), str(enrichment), str(enriched))):
            result = run(*args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return enriched

    def test_bare_tie_report_under_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = run("scripts/build_visualization_plan.py", str(TIE), str(Path(tmp) / "plan.json"), *priority_args())
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("CUSTOMER_MIN_VISUALS_NOT_MET", p.stdout + p.stderr)

    def test_plan_and_model_agree_under_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, model, decision = self.build(Path(tmp), self.enriched_tie(Path(tmp)), priority_args())
            self.assertEqual(plan["top_levers"], [f["id"] for f in model["findings"]])
            self.assertEqual(plan["top_levers"], ["F-001", "F-003", "F-004", "F-005"])
            self.assertEqual(decision["legacy_selected_ids"], ["F-001", "F-003", "F-004", "F-002"])
            self.assertTrue(decision["synthetic_test_profile"])
            self.assertNotIn("SYNTHETIC_SAMPLE_01", json.dumps(model))

    def test_non_tie_keeps_legacy_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, model, decision = self.build(Path(tmp), FIX / "synthetic-report.json", priority_args())
            self.assertEqual(plan["top_levers"], ["F-001", "F-003", "F-004", "F-002"])
            self.assertEqual(decision["deviations"], [])

    def test_synthetic_catalog_ignored_without_test_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, model, decision = self.build(Path(tmp), TIE, priority_args(test_mode=False))
            self.assertEqual(plan["top_levers"], ["F-001", "F-003", "F-004", "F-002"])
            self.assertEqual(decision["mode"], "LEGACY_PRIORITY")

    def test_model_refuses_plan_with_other_levers(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            self.assertEqual(run("scripts/build_visualization_plan.py", str(TIE), str(t / "plan.json")).returncode, 0)
            m = run("scripts/build_client_report_model.py", str(TIE), str(t / "model.json"),
                    "--visual-plan", str(t / "plan.json"), *priority_args())
            self.assertNotEqual(m.returncode, 0)
            self.assertIn("top_levers", m.stdout + m.stderr)

    def test_catalog_digest_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = ["--priority-context", str(CONTEXT), "--priority-catalog", str(CATALOG),
                   "--priority-catalog-sha256", "0" * 64]
            self.assertNotEqual(run("scripts/build_visualization_plan.py", str(TIE), str(Path(tmp) / "p.json"), *bad).returncode, 0)


if __name__ == "__main__":
    unittest.main()
