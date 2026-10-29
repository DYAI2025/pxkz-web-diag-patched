"""Positive end-to-end customer build with four or more admissible visuals and a closed evidence chain.

Counterpart to the fail-closed Baumdienst and low-coverage cases (test_customer_claim_scope.py): the
active-core fixture path (synthetic report + full-48 core execution bundle) materializes every core
metric from a declared evidence catalog, so each selected visual traces back to metric evidence. The
fixture data is synthetic and says so in every evidence row (claim_boundary); this test proves the
contract, not a real customer result. Because the data is fixture data, the full chain is built in
proof mode with the strict exact-font contract, and the same input must be refused in customer mode
(evidence-bound claims patch: example data is never presented as a live customer result). Without the
declared PDF runtime the test is skipped and must be reported as not run.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from test_packaged_brand_fonts import HAS_PDF_RUNTIME, isolated_env  # noqa: E402
from visualization_policy import CUSTOMER_FORBIDDEN_TEMPLATES, CUSTOMER_MAX_VISUALS, CUSTOMER_MIN_VISUALS  # noqa: E402

BUNDLE_PATH = ROOT / "evals/fixtures/full-48-core-execution.json"
# The bundle is fixture data: the PDF names it as example data instead of claiming a page sample.
SCOPE_SENTENCE = "Grundlage: Beispieldaten, keine Live-Messung."


@unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime (WeasyPrint/PyMuPDF/fontTools) unavailable: positive customer E2E NOT RUN")
class PositiveCustomerEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="pxk-positive-e2e-")
        tmp = Path(cls._tmp.name)
        env = isolated_env(tmp)
        materialized, cls.scored_path = tmp / "materialized.json", tmp / "scored.json"

        def run(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, env=env)

        steps = [
            run(str(ROOT / "scripts/materialize_core_metrics.py"), str(ROOT), str(ROOT / "evals/fixtures/synthetic-report.json"),
                str(BUNDLE_PATH), str(materialized), "--admission-out", str(tmp / "admission.json")),
        ]
        steps.append(run(str(ROOT / "scripts/compute_score.py"), str(materialized), str(cls.scored_path)))
        cls.out = tmp / "deliverables"
        steps.append(run(str(ROOT / "scripts/build_audit_deliverables.py"), str(cls.scored_path), str(cls.out),
                         "--release-mode", "proof", "--require-exact-fonts", "--force-svg-fallback"))
        cls.steps = steps
        cls.customer_attempt = run(str(ROOT / "scripts/build_audit_deliverables.py"), str(cls.scored_path), str(tmp / "customer"),
                                   "--release-mode", "customer", "--force-svg-fallback")
        cls.customer_dir = tmp / "customer"
        cls.network_log = tmp / "network.log"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def load(self, name: str) -> dict:
        return json.loads((self.out / name).read_text(encoding="utf-8"))

    def test_pipeline_builds_a_strict_customer_bundle(self):
        for proc in self.steps:
            self.assertEqual(proc.returncode, 0, proc.stdout[-2000:] + proc.stderr[-3000:])
        receipt = self.load("presentation-render-receipt.json")
        self.assertEqual(receipt["brand_font_status"], "EXACT")
        self.assertEqual(receipt["pdf_font_embedding"]["status"], "VERIFIED")
        self.assertEqual(self.load("deliverable-manifest.json")["status"], "BUILT_PENDING_QA")
        self.assertFalse(self.network_log.exists() and self.network_log.read_text(encoding="utf-8").strip())

    def test_fixture_evidence_is_refused_in_customer_mode(self):
        self.assertNotEqual(self.customer_attempt.returncode, 0)
        self.assertIn("SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT", self.customer_attempt.stdout + self.customer_attempt.stderr)
        self.assertFalse((self.customer_dir / "customer_presentation.pdf").exists())

    def test_at_least_four_admissible_visuals_and_none_forbidden(self):
        selected = [v for v in self.load("visualization-plan.json")["visuals"] if v.get("status") == "SELECTED"]
        ids = {v["template_id"] for v in selected}
        self.assertGreaterEqual(len(selected), CUSTOMER_MIN_VISUALS)
        self.assertLessEqual(len(selected), CUSTOMER_MAX_VISUALS)
        self.assertFalse(ids & CUSTOMER_FORBIDDEN_TEMPLATES, ids)
        receipt = self.load("presentation-render-receipt.json")
        self.assertEqual(receipt["embedded_visual_count"], len(selected))

    def test_every_selected_visual_traces_to_resolvable_target_bound_evidence(self):
        scored = json.loads(self.scored_path.read_text(encoding="utf-8"))
        bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
        catalog = {e["id"]: e for e in bundle["evidence_catalog"]}
        metrics = {m["id"]: m for m in scored["metrics"]}
        categories = {c["category"] for c in scored["score_summary"]["category_scores"]}
        plan = self.load("visualization-plan.json")
        for visual in (v for v in plan["visuals"] if v.get("status") == "SELECTED"):
            refs = visual.get("metric_refs") or []
            self.assertTrue(refs, visual["template_id"])
            for ref in refs:
                if ref.startswith("CATEGORY:"):
                    self.assertIn(ref.split(":", 1)[1], categories, (visual["template_id"], ref))
                    continue
                self.assertIn(ref, metrics, (visual["template_id"], ref))
                evidence_refs = metrics[ref].get("evidence_refs") or []
                self.assertTrue(evidence_refs, (visual["template_id"], ref))
                for evidence_id in evidence_refs:
                    self.assertIn(evidence_id, catalog, (ref, evidence_id))
                    self.assertEqual(catalog[evidence_id]["target_url"], bundle["target_url"], (ref, evidence_id))
        for lever in plan["top_levers"]:
            finding = next(f for f in scored["findings"] if f["id"] == lever)
            self.assertTrue(finding.get("evidence"), lever)

    def test_customer_pdf_states_its_sampling_and_ai_boundary(self):
        import fitz

        with fitz.open(self.out / "customer_presentation.pdf") as doc:
            text = " ".join(" ".join(page.get_text().split()) for page in doc)
        self.assertIn(SCOPE_SENTENCE, text)
        self.assertIn("KI-Antworten wurden nicht abgefragt.", text)

    def test_internal_report_never_claims_a_verified_browser_run(self):
        capabilities = self.load("diagnosis-report.json")["coverage"]["capabilities"]
        note = next(c["note"] for c in capabilities if c["id"] == "public_page_render")
        self.assertIn("browser_execution_independently_verified=false", note)
        self.assertNotIn("browser_render_executed", note)


if __name__ == "__main__":
    unittest.main()
