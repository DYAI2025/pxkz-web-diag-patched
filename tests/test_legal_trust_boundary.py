"""Legal customer-risk findings are admitted only as the exact projection of a supplied sidecar."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from attach_impressum_findings import finding_from  # noqa: E402
from impressum_compliance import assess_case  # noqa: E402
from legal_customer_projection import contested_legal_surface, resolve_projection  # noqa: E402
from validate_impressum_projection import validate  # noqa: E402

CASES = json.loads((ROOT / "evals/fixtures/impressum-compliance-cases.json").read_text(encoding="utf-8"))["cases"]
GOLDEN = next(c for c in CASES if c.get("id") == "LEG-GOLD-BFL")


def golden_sidecar() -> dict:
    return assess_case(GOLDEN["context"], GOLDEN["observations"], root=ROOT, discovery_scope={"complete": True})


def report_with(finding: dict) -> dict:
    report = json.loads((ROOT / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
    report["findings"].append(finding)
    return report


class ProjectionValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sidecar = golden_sidecar()
        self.finding = finding_from(self.sidecar, 99)

    def test_genuine_projection_passes(self) -> None:
        self.assertEqual(validate(self.sidecar, report_with(self.finding)), [])

    def test_internal_only_sidecar_rejects_any_legal_finding(self) -> None:
        empty = {"results": []}
        self.assertEqual(resolve_projection(empty)["priority"], "INTERNAL_ONLY")
        errors = validate(empty, report_with(self.finding))
        self.assertTrue(any("INTERNAL_ONLY" in e for e in errors), errors)

    def test_group_must_match_resolver(self) -> None:
        forged = copy.deepcopy(self.finding)
        forged["customer_risk"]["group"] = "PROVIDER_INFORMATION" if forged["customer_risk"]["group"] == "PROVIDER_IDENTITY" else "PROVIDER_IDENTITY"
        self.assertIn("customer_risk group does not match resolver", validate(self.sidecar, report_with(forged)))

    def test_legal_refs_must_equal_resolver(self) -> None:
        forged = copy.deepcopy(self.finding)
        forged["customer_risk"]["legal_metric_refs"] = forged["customer_risk"]["legal_metric_refs"] + ["LEGAL-IMP-11"]
        forged["metric_refs"] = forged["metric_refs"] + ["LEGAL-IMP-11"]
        self.assertIn("customer_risk legal_metric_refs do not match resolver", validate(self.sidecar, report_with(forged)))

    def test_second_legal_finding_is_rejected(self) -> None:
        stray = copy.deepcopy(self.finding)
        stray["id"] = "F-930"
        report = report_with(self.finding)
        report["findings"].append(stray)
        self.assertTrue(any("exactly one" in e for e in validate(self.sidecar, report)))


class BuilderRequiresSidecarTest(unittest.TestCase):
    def test_legal_claim_without_sidecar_fails_closed(self) -> None:
        finding = finding_from(golden_sidecar(), 99)
        with tempfile.TemporaryDirectory(prefix="pxk-legal-boundary-") as td:
            t = Path(td)
            src = t / "report.json"
            src.write_text(json.dumps(report_with(finding), ensure_ascii=False), encoding="utf-8")
            scored = t / "scored.json"
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/compute_score.py"), str(src), str(scored)], check=True, capture_output=True)
            proc = subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts/build_audit_deliverables.py"), str(scored), str(t / "out"), "--release-mode", "proof"],
                capture_output=True, text=True, timeout=300,
            )
        self.assertNotEqual(proc.returncode, 0, proc.stdout[-500:])
        self.assertIn("LEGAL_SIDECAR_REQUIRED", proc.stderr + proc.stdout)


class LegalSurfaceStatusTest(unittest.TestCase):
    """A projected legal customer risk must not sit next to a 'Klar' legal-surface row in the trust matrix."""

    def trust_row(self, report: dict) -> dict:
        with tempfile.TemporaryDirectory(prefix="pxk-legal-surface-") as td:
            t = Path(td)
            src, scored, plan = t / "report.json", t / "scored.json", t / "plan.json"
            src.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/compute_score.py"), str(src), str(scored)], check=True, capture_output=True)
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build_visualization_plan.py"), str(scored), str(plan)], check=True, capture_output=True)
            data = json.loads(plan.read_text(encoding="utf-8"))
        trust = next(v for v in data["visuals"] if v["template_id"] == "V10_TRUST_MATRIX")
        return next(r for r in trust["data"] if "impressum" in r["signal"].casefold())

    def test_helper_only_reacts_to_projected_risk(self) -> None:
        self.assertEqual(contested_legal_surface({"findings": [{"id": "F-1"}]}), frozenset())
        self.assertEqual(contested_legal_surface({"findings": [{"id": "F-1", "customer_risk": {}}]}), frozenset())
        self.assertEqual(contested_legal_surface(report_with(finding_from(golden_sidecar(), 99))), frozenset({"TRUST-01"}))

    def test_trust_row_follows_legal_risk(self) -> None:
        base = json.loads((ROOT / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
        self.assertEqual(self.trust_row(base)["status"], "Klar")
        self.assertEqual(self.trust_row(report_with(finding_from(golden_sidecar(), 99)))["status"], "Handlungsbedarf")


class CitedMetricNotClearTest(unittest.TestCase):
    """A metric cited by a customer-visible problem finding must not read as clear in the status matrices."""

    def rows(self, report: dict) -> dict[str, str]:
        with tempfile.TemporaryDirectory(prefix="pxk-cited-") as td:
            t = Path(td)
            src, scored, plan = t / "report.json", t / "scored.json", t / "plan.json"
            src.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/compute_score.py"), str(src), str(scored)], check=True, capture_output=True)
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build_visualization_plan.py"), str(scored), str(plan)], check=True, capture_output=True)
            data = json.loads(plan.read_text(encoding="utf-8"))
        self.values = {(r.get("signal") or r.get("question")): r["value"] for v in data["visuals"]
                       if v["template_id"] == "V08_AI_ANSWERABILITY" for r in v["data"]}
        return {(r.get("signal") or r.get("question")): r["status"] for v in data["visuals"]
                if v["template_id"] in {"V08_AI_ANSWERABILITY", "V10_TRUST_MATRIX"} for r in v["data"]}

    def test_problem_finding_caps_cited_metric(self) -> None:
        base = json.loads((ROOT / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
        self.assertEqual(self.rows(base)["Kontakttransparenz"], "Klar")
        cited = copy.deepcopy(base)
        cited["findings"].append({**copy.deepcopy(next(f for f in base["findings"] if f.get("severity") == "medium")),
                                  "id": "F-940", "metric_refs": ["TRUST-07"]})
        self.assertEqual(self.rows(cited)["Kontakttransparenz"], "Verbesserung sinnvoll")

    def test_identity_rows_not_clear_next_to_identity_risk(self) -> None:
        rows = self.rows(report_with(finding_from(golden_sidecar(), 99)))
        for label in ("Eindeutige Unternehmensdarstellung", "Fakten überall gleich", "Kontakttransparenz"):
            self.assertNotIn(rows[label], {"Klar", "klar"}, label)
        # The matrix tint is a scale over value; a capped row must sit on the template's "teilweise" anchor,
        # not at a value that both renderers paint as clear.
        for label in ("Eindeutige Unternehmensdarstellung", "Fakten überall gleich"):
            self.assertLessEqual(self.values[label], 0.5, label)
        self.assertEqual(rows["Impressum und rechtliche Angaben"], "Handlungsbedarf")


if __name__ == "__main__":
    unittest.main()
