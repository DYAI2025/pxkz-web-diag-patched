"""Customer claims stay inside what the audit measured (PXK-BUG-001).

SEM-001: sampled public pages never read as a whole-site fact.
SEM-002: machine extractability and answerability never read as AI answers, citations or rankings.
SEM-003: the finding-count visual is internal-only; fewer than four admissible visuals block the customer plan.
"""
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

from client_story import clientize  # noqa: E402
from validate_customer_output_guardrails import claim_violations  # noqa: E402
from visualization_policy import CUSTOMER_FORBIDDEN_TEMPLATES  # noqa: E402


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True)


def hits(text: str, *, scope: bool = True) -> set[str]:
    return {name for name, _ in claim_violations(text, scope=scope)}


class GuardrailPatternTests(unittest.TestCase):
    def test_flags_universal_scope_and_ai_visibility(self) -> None:
        for text, expected in (
            ("Firmendaten auf allen Seiten", {"universal_scope"}),
            ("Fakten überall gleich", {"universal_scope"}),
            ("Die Preise stehen auf jeder Seite", {"universal_scope"}),
            ("Wie klar die Website für KI-Systeme ist", {"ai_visibility_overclaim"}),
            ("Ihr Betrieb wird in ChatGPT genannt", {"ai_visibility_overclaim"}),
            ("KI-Systeme empfehlen Ihren Betrieb", {"ai_visibility_overclaim"}),
            ("Mehr KI-Sichtbarkeit für Ihr Angebot", {"ai_visibility_overclaim"}),
            # Singular verbs, SVO order and synonyms found in review.
            ("ChatGPT empfiehlt deshalb Ihre Konkurrenz", {"ai_visibility_overclaim"}),
            ("ChatGPT nennt Ihren Betrieb nicht", {"ai_visibility_overclaim"}),
            ("Die KI empfiehlt Ihre Konkurrenz", {"ai_visibility_overclaim"}),
            ("ChatGPT zitiert Ihre Website", {"ai_visibility_overclaim"}),
            ("Ihr Betrieb erscheint nicht in KI-Antworten", {"ai_visibility_overclaim"}),
            ("Ihr Betrieb taucht in KI-Antworten nicht auf", {"ai_visibility_overclaim"}),
            ("Wird in KI-Suchen seltener gefunden", {"ai_visibility_overclaim"}),
            ("Ihre KI-Suchsichtbarkeit sinkt", {"ai_visibility_overclaim"}),
            ("Mehr KI-/Suchsichtbarkeit", {"ai_visibility_overclaim"}),
            ("Weniger KI-Zitation", {"ai_visibility_overclaim"}),
            ("Die Kontaktdaten sind auf allen Unterseiten identisch", {"universal_scope"}),
            ("Auf sämtlichen Leistungsseiten fehlt ein Preis", {"universal_scope"}),
            ("Die Firmendaten sind überall identisch", {"universal_scope"}),
            ("Die Angaben sind überall einheitlich", {"universal_scope"}),
            ("Auf der gesamten Website fehlen Belege", {"universal_scope"}),
            ("Durchgängig gleiche Firmendaten", {"universal_scope"}),
            ("Jede Seite zeigt dieselbe Adresse", {"universal_scope"}),
            ("Alle Leistungsseiten sind gleich aufgebaut", {"universal_scope"}),
        ):
            with self.subTest(text=text):
                self.assertEqual(hits(text), expected)

    def test_accepts_scoped_customer_wording(self) -> None:
        for text in (
            "Einheitliche Firmendaten", "Einheitliche Fakten", "Wie eindeutig die Website Fragen beantwortet",
            "Firmendaten überall angleichen", "Such- und KI-Systeme finden weniger klare Antworten.",
            "KI-Verständlichkeit",
            # Measurement-boundary disclaimers are not claims.
            "Wirkung auf Leads oder KI-Nennungen wurde nicht gemessen.",
            "Maschinenlesbare Antworten belegen keine Nennung, Zitierung oder Platzierung in KI-Antworten.",
        ):
            with self.subTest(text=text):
                self.assertEqual(hits(text), set())

    def test_target_state_actions_are_not_scope_claims(self) -> None:
        action = "Telefonnummer und Anfrage-Button auf jeder Seite im Kopfbereich zeigen."
        self.assertEqual(hits(action, scope=False), set())
        self.assertEqual(hits(action), {"universal_scope"})

    def test_registry_labels_are_clientized_without_universal_scope(self) -> None:
        for label in ("Konsistente Unternehmens- & Leistungsdaten", "Faktenkonsistenz über Seiten hinweg",
                      "Fakten auf allen Seiten gleich"):
            with self.subTest(label=label):
                self.assertEqual(hits(clientize(label, 130)), set())


class VisualPlanTests(unittest.TestCase):
    def build_plan(self, fixture: str, tmp: Path) -> tuple[subprocess.CompletedProcess, Path, Path]:
        scored, plan = tmp / f"{fixture}.scored.json", tmp / f"{fixture}.plan.json"
        self.assertEqual(run("scripts/compute_score.py", f"evals/fixtures/{fixture}.json", str(scored)).returncode, 0)
        return run("scripts/build_visualization_plan.py", str(scored), str(plan)), scored, plan

    def test_finding_count_visual_is_internal_only(self) -> None:
        self.assertIn("V11_SEVERITY_DISTRIBUTION", CUSTOMER_FORBIDDEN_TEMPLATES)
        with tempfile.TemporaryDirectory() as td:
            result, scored, plan_path = self.build_plan("synthetic-report", Path(td))
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            selected = {v["template_id"] for v in plan["visuals"] if v["status"] == "SELECTED"}
            self.assertFalse(selected & CUSTOMER_FORBIDDEN_TEMPLATES)
            excluded = {x["template_id"]: x["reason"] for x in plan["excluded_candidates"]}
            self.assertEqual(excluded["V11_SEVERITY_DISTRIBUTION"], "INTERNAL_ONLY_FINDING_COUNT_WITHOUT_STRATEGIC_RELEVANCE")
            v08 = next(v for v in plan["visuals"] if v["template_id"] == "V08_AI_ANSWERABILITY")
            self.assertEqual(hits(v08["title"] + " " + v08["subtitle"]), set())
            self.assertIn("keine Nennung, Zitierung oder Platzierung in KI-Antworten", v08["does_not_prove"])
            rows = " ".join(str(r.get("question") or r.get("signal")) for v in plan["visuals"] for r in v.get("data", [])
                            if isinstance(r, dict))
            self.assertEqual(hits(rows), set())

            # The plan validator rejects a finding-count visual even when a builder lets one through.
            forged = copy.deepcopy(plan)
            extra = copy.deepcopy(forged["visuals"][-1])
            extra.update({"id": "VIZ-099", "template_id": "V11_SEVERITY_DISTRIBUTION"})
            forged["visuals"].append(extra)
            forged_path = Path(td) / "forged.plan.json"
            forged_path.write_text(json.dumps(forged, ensure_ascii=False), encoding="utf-8")
            rejected = run("scripts/validate_visualization_plan.py", str(forged_path), str(scored))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("internal-only visual", rejected.stderr)

    def test_fewer_than_four_admissible_visuals_block_the_customer_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for fixture in ("baumdienst-renner-reflection-regression", "low-coverage-marketing-report"):
                with self.subTest(fixture=fixture):
                    result, _, plan_path = self.build_plan(fixture, Path(td))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("CUSTOMER_RELEASE_BLOCKED: CUSTOMER_MIN_VISUALS_NOT_MET", result.stderr)
                    self.assertIn("got 3", result.stderr)
                    self.assertFalse(plan_path.exists())


if __name__ == "__main__":
    unittest.main()
