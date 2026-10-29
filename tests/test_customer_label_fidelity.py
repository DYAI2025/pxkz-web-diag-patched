"""Customer labels say no more than the measurement they summarize (release completion review findings).

Ranking chart: a device, place or date in the subtitle must hold for every plotted query.
Website symbol: a declared icon that failed to load is not a missing icon.
Strengths: while a legal customer risk is projected, no strength vouches for the legal or contact surface;
presence checks back no strength at all.
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

from attach_impressum_findings import finding_from  # noqa: E402
from attach_vibecheck03_findings import attach  # noqa: E402
from impressum_compliance import assess_case  # noqa: E402
from vibecheck03 import observe  # noqa: E402

PAGE = "https://example.com/"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True)


def serp(query: str, device: str, position: int) -> list[dict]:
    common = {"query": query, "device": device, "location": "Berlin,Germany", "observed_at": "2026-10-28T21:25:54Z",
              "status": "MEASURED", "source_provider": "fixture"}
    return [dict(common, id="SERP_CURRENT_POSITION", value=position), dict(common, id="SERP_CURRENT_PAGE", value=1)]


class RankingSubtitleTests(unittest.TestCase):
    def ranking_subtitle(self, devices: list[str]) -> str:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = tmp / "scored.json"
            self.assertEqual(run("scripts/compute_score.py", "evals/fixtures/synthetic-report.json", str(scored)).returncode, 0)
            report = json.loads(scored.read_text(encoding="utf-8"))
            metrics = []
            for i, device in enumerate(devices):
                metrics += serp(f"anfrage {i}", device, 9 + i)
            report["measurement_enrichment"] = {"metrics": metrics}
            scored.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            plan = tmp / "plan.json"
            result = run("scripts/build_visualization_plan.py", str(scored), str(plan))
            self.assertEqual(result.returncode, 0, result.stderr)
            visuals = [v for v in json.loads(plan.read_text(encoding="utf-8"))["visuals"] if v["template_id"] == "V05_RANKING_POSITION"]
            self.assertEqual(len(visuals), 1)
            return visuals[0]["subtitle"]

    def test_mixed_devices_are_not_labelled_with_the_first_device(self) -> None:
        subtitle = self.ranking_subtitle(["mobile", "desktop"])
        self.assertIn("Mobil", subtitle)
        self.assertIn("Desktop", subtitle)

    def test_single_device_keeps_its_label(self) -> None:
        subtitle = self.ranking_subtitle(["mobile", "mobile"])
        self.assertEqual(subtitle, "Berlin, Deutschland · Mobil · 28.10.2026")


class WebsiteSymbolCopyTests(unittest.TestCase):
    def lever_copy(self, html: str) -> dict:
        report = json.loads((ROOT / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
        report = copy.deepcopy(report)
        report["meta"]["audit_id"] = "vc03-icon"
        vc = observe({"run_id": "vc03-icon", "page_url": report["meta"]["audited_url"], "html": html, "html_complete": True,
                      "observed_at": "2026-10-27T10:00:00+01:00", "asset_results": {"https://example.com/icon.png": False}})
        attached = attach(report, vc)
        icons = [f for f in attached["findings"] if "Website-Symbol" in f.get("title", "")]
        self.assertEqual(len(icons), 1)
        return icons[0]

    def test_declared_icon_that_fails_to_load_is_not_called_missing(self) -> None:
        finding = self.lever_copy("<html><head><title>T</title><link rel='icon' href='/icon.png'></head><body></body></html>")
        customer_text = " ".join(str(finding.get(k) or "") for k in ("title", "client_title", "client_observation", "client_action", "client_impact"))
        self.assertNotIn("Kein eigenes", customer_text)
        self.assertNotIn("hinterlegen", customer_text)
        self.assertIn("abrufbar", customer_text)


class LegalSurfaceStrengthTests(unittest.TestCase):
    def strengths(self, *, legal_risk: bool, claims: list | None = None) -> list[str]:
        report = json.loads((ROOT / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
        if legal_risk:
            golden = next(c for c in json.loads((ROOT / "evals/fixtures/impressum-compliance-cases.json").read_text(encoding="utf-8"))["cases"]
                          if c.get("id") == "LEG-GOLD-BFL")
            sidecar = assess_case(golden["context"], golden["observations"], root=ROOT, discovery_scope={"complete": True})
            report["findings"].append(finding_from(sidecar, 99))
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            src, scored, model = tmp / "report.json", tmp / "scored.json", tmp / "model.json"
            src.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run("scripts/compute_score.py", str(src), str(scored)).returncode, 0)
            bindings = tmp / "bindings.json"
            result = run("scripts/build_client_report_model.py", str(scored), str(model), "--claim-bindings-out", str(bindings))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            if claims is not None:
                claims.extend(json.loads(bindings.read_text(encoding="utf-8"))["claims"])
            return json.loads(model.read_text(encoding="utf-8"))["executive"]["strengths"]

    def test_projected_legal_risk_drops_legal_surface_strength(self) -> None:
        strengths = self.strengths(legal_risk=True)
        self.assertFalse([s for s in strengths if "Rechts" in s or "Impressum" in s or "Kontakt" in s], strengths)
        # Strengths are bound to positive findings whose metrics read "Klar" (evidence-bound claims patch).
        # F-006 (TRUST-01/02/03/07) is contested by the projected legal risk; F-007 (FIND-02/03 at 75,
        # "Verbesserung sinnvoll") does not read "Klar". Free-text top_strengths have no metric link.
        self.assertEqual(strengths, [])

    def test_without_legal_risk_only_the_presence_reading_withholds_the_strength(self) -> None:
        # Owner decision 2026-10-29: TRUST-01/02 are presence checks and read "(vorhanden) · Nicht belastbar bewertet",
        # so "gut erreichbar" claims more than they show. Without a legal risk nothing is contested.
        claims: list = []
        self.assertEqual(self.strengths(legal_risk=False, claims=claims), [])
        f006 = next(c for c in claims if c["finding_ref"] == "F-006")
        self.assertEqual(f006["reasons"], ["METRIC_NOT_CLEAR:TRUST-01", "METRIC_NOT_CLEAR:TRUST-02"])


if __name__ == "__main__":
    unittest.main()
