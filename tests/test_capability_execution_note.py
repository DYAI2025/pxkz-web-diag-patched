"""A text-only observation must not read as an executed browser render (PXK-BUG-002, bounded fix A).

The capability status rule is unchanged (it feeds score admission). source_family is declared by the
execution bundle and no browser artifact is verified, so the public_page_render note records only the
declared source class and states that browser execution is not independently verified.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core_active_measurement import materialize_report  # noqa: E402

BASE = json.loads((ROOT / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
BUNDLE = json.loads((ROOT / "evals/fixtures/full-48-core-execution.json").read_text(encoding="utf-8"))
REGISTRY = {m["id"]: m for m in json.loads((ROOT / "assets/measurement-registry.json").read_text(encoding="utf-8"))["metrics"]}


def render_note(bundle: dict) -> dict:
    report, _ = materialize_report(ROOT, copy.deepcopy(BASE), bundle)
    return next(c for c in report["coverage"]["capabilities"] if c["id"] == "public_page_render")


class CapabilityExecutionNoteTests(unittest.TestCase):
    def test_note_reports_the_declared_source_class_only(self) -> None:
        families = {r["source_family"] for r in BUNDLE["results"]
                    if REGISTRY[r["metric_id"]]["capability_id"] == "public_page_render"}
        row = render_note(BUNDLE)
        self.assertEqual(row["status"], "available")
        declared = "BROWSER_RENDERING" in families
        self.assertIn(f"browser_rendering_source_declared={'true' if declared else 'false'}", row["note"])
        self.assertIn("browser_execution_independently_verified=false", row["note"])
        self.assertNotIn("browser_render_executed", row["note"])
        self.assertIn("scoreable_source_families=", row["note"])

    def test_text_only_observation_is_not_reported_as_render(self) -> None:
        bundle = copy.deepcopy(BUNDLE)
        render_ids = {m for m, d in REGISTRY.items() if d["capability_id"] == "public_page_render"}
        refs = set()
        for result in bundle["results"]:
            if result["metric_id"] in render_ids:
                result["source_family"] = "RULE_BASED_QUALITATIVE_OBSERVATION"
                refs.update(result["evidence_refs"])
        for evidence in bundle["evidence_catalog"]:
            if evidence["id"] in refs:
                evidence["source_family"] = "RULE_BASED_QUALITATIVE_OBSERVATION"
        row = render_note(bundle)
        self.assertEqual(row["status"], "available")  # admission is unchanged by design
        self.assertIn("browser_rendering_source_declared=false", row["note"])
        self.assertIn("browser_execution_independently_verified=false", row["note"])
        self.assertIn("scoreable_source_families=RULE_BASED_QUALITATIVE_OBSERVATION", row["note"])

    def test_other_capability_notes_are_unchanged(self) -> None:
        report, _ = materialize_report(ROOT, copy.deepcopy(BASE), BUNDLE)
        for row in report["coverage"]["capabilities"]:
            if row["id"] != "public_page_render":
                self.assertEqual(row["note"], "derived from active core execution bundle")


if __name__ == "__main__":
    unittest.main()
