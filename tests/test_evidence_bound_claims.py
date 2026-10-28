"""Evidence-bound customer claims: measurements survive simplification; claims bind to scored truth.

Eight regression cases from the 2026-10-28 evidence-bound claims fix slice. Cases marked CANARY were
already fixed in a66710f and must stay green; the others were red on 6db8fb1.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from client_story import clientize  # noqa: E402
from customer_status import STATUS_META  # noqa: E402

FIXTURE = ROOT / "evals/fixtures/synthetic-report.json"
LAB_SENTENCE = "Der wichtigste sichtbare Inhalt erscheint im mobilen Labortest spürbar verzögert."
HAS_PDF_RUNTIME = importlib.util.find_spec("weasyprint") is not None and importlib.util.find_spec("pypdf") is not None


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *args], cwd=cwd, capture_output=True, text=True)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scored_from(report: dict, tmp: Path, name: str = "scored") -> Path:
    src, out = tmp / f"{name}.input.json", tmp / f"{name}.json"
    dump(src, report)
    result = run("scripts/compute_score.py", str(src), str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    return out


def set_metric(report: dict, metric_id: str, *, score: int, status: str) -> None:
    for m in report["metrics"]:
        if m["id"] == metric_id:
            m["score"], m["status"], m["measurement_class"] = score, status, "measured"
            return
    raise KeyError(metric_id)


def build_plan(scored: Path, tmp: Path) -> dict:
    plan = tmp / "plan.json"
    result = run("scripts/build_visualization_plan.py", str(scored), str(plan))
    assert result.returncode == 0, result.stdout + result.stderr
    return load(plan)


class Case1LabStaysLab(unittest.TestCase):
    def test_mobile_lab_sentence_is_not_rewritten_to_real_mobile(self) -> None:
        text = clientize(LAB_SENTENCE, 200)
        self.assertNotIn("auf Mobilgeräten", text)
        self.assertIn("Testmessung", text)

    def test_bare_lab_word_keeps_method(self) -> None:
        self.assertIn("Testmessung", clientize("Im Labortest lädt die Seite langsam.", 200))


class Case2SyntheticStaysSynthetic(unittest.TestCase):
    def test_synthetic_wording_is_not_called_documented(self) -> None:
        for raw in ("Mobile Ladezeit · synthetische Testreihe", "Synthetic fixture 1.0", "synthetisches Testfeld"):
            text = clientize(raw, 200)
            self.assertNotIn("dokumentiert", text, raw)
            self.assertIn("Beispieldaten", text, raw)

    def test_synthetic_v07_is_marked_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plan = build_plan(scored_from(load(FIXTURE), tmp), tmp)
            v07 = [v for v in plan["visuals"] if v["template_id"] == "V07_PERFORMANCE_THRESHOLD"]
            self.assertEqual(len(v07), 1)
            self.assertEqual(v07[0]["evidence_method"], "SYNTHETIC")
            self.assertIn("Beispieldaten", v07[0]["subtitle"])

    @unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime missing: NOT RUN")
    def test_synthetic_evidence_blocks_customer_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = scored_from(load(FIXTURE), tmp)
            result = run("scripts/build_audit_deliverables.py", str(scored), str(tmp / "out"), "--release-mode", "customer", "--force-svg-fallback")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT", result.stdout + result.stderr)
            self.assertFalse((tmp / "out" / "customer_presentation.pdf").exists())


class Case3SampleScopeStaysVisible(unittest.TestCase):
    def test_ai06_claim_never_says_whole_site(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            report = load(FIXTURE)
            set_metric(report, "AI-06", score=100, status="strong")
            positive = copy.deepcopy(next(f for f in report["findings"] if f["id"] == "F-006"))
            positive.update({
                "id": "F-900", "category": "ai_readiness", "title": "Fakten sind über die Seiten konsistent",
                "client_observation": "Fakten sind auf der gesamten Website konsistent.", "metric_refs": ["AI-06"],
            })
            report["findings"].append(positive)
            scored = scored_from(report, tmp)
            model = tmp / "model.json"
            result = run("scripts/build_client_report_model.py", str(scored), str(model))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            strengths = load(model)["executive"]["strengths"]
            joined = " ".join(strengths)
            self.assertNotIn("gesamte", joined)
            self.assertNotIn("alle Seiten", joined)
            self.assertTrue(any("geprüften Seiten" in s for s in strengths), strengths)


class Case4OneStatusScale(unittest.TestCase):
    def test_v08_and_v10_label_75_identically(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            report = load(FIXTURE)
            set_metric(report, "AI-01", score=75, status="minor_gaps")
            set_metric(report, "TRUST-04", score=75, status="minor_gaps")
            visuals = {v["template_id"]: v for v in build_plan(scored_from(report, tmp), tmp)["visuals"]}
            v08 = next(r for r in visuals["V08_AI_ANSWERABILITY"]["data"] if r.get("metric_ref") == "AI-01")
            v10 = next(r for r in visuals["V10_TRUST_MATRIX"]["data"] if r.get("metric_ref") == "TRUST-04")
            self.assertEqual(v08["status"], STATUS_META["IMPROVE"]["label"])
            self.assertEqual(v10["status"], STATUS_META["IMPROVE"]["label"])
            self.assertEqual(v08["value"], v10["value"])
            labels = {m["label"] for m in STATUS_META.values()}
            for tid in ("V08_AI_ANSWERABILITY", "V10_TRUST_MATRIX"):
                for row in visuals[tid]["data"]:
                    self.assertIn(row["status"], labels, (tid, row))


class Case5NoOppositeStrength(unittest.TestCase):
    def test_zero_trust_metrics_yield_no_contact_or_privacy_strength(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            report = load(FIXTURE)
            set_metric(report, "TRUST-01", score=25, status="weak")
            set_metric(report, "TRUST-02", score=0, status="blocking")
            set_metric(report, "TRUST-07", score=0, status="blocking")
            scored = scored_from(report, tmp)
            model, bindings = tmp / "model.json", tmp / "bindings.json"
            result = run("scripts/build_client_report_model.py", str(scored), str(model), "--claim-bindings-out", str(bindings))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            strengths = load(model)["executive"]["strengths"]
            for s in strengths:
                for word in ("Kontakt", "Impressum", "Datenschutz", "Rechts"):
                    self.assertNotIn(word, s, strengths)
            rows = load(bindings)["claims"]
            self.assertTrue(rows, "sidecar must list every candidate claim")
            admitted = [r for r in rows if r["admitted"]]
            self.assertEqual(sorted(r["text"] for r in admitted), sorted(strengths))
            for r in admitted:
                self.assertTrue(r["metric_refs"], r)
                self.assertFalse(set(r["metric_refs"]) & {"TRUST-01", "TRUST-02", "TRUST-07"}, r)
            check = run("scripts/validate_customer_claim_bindings.py", str(scored), str(model), str(bindings))
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_validator_rejects_a_strength_backed_by_a_blocking_metric(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            report = load(FIXTURE)
            scored = scored_from(report, tmp)
            model, bindings = tmp / "model.json", tmp / "bindings.json"
            self.assertEqual(run("scripts/build_client_report_model.py", str(scored), str(model), "--claim-bindings-out", str(bindings)).returncode, 0)
            # Same model + sidecar, but the scored truth now says the contact surface is blocking.
            truth = load(scored)
            set_metric(truth, "TRUST-07", score=0, status="blocking")
            dump(scored, truth)
            check = run("scripts/validate_customer_claim_bindings.py", str(scored), str(model), str(bindings))
            self.assertNotEqual(check.returncode, 0)
            self.assertIn("CLAIM_BINDING_FAIL", check.stdout)


class Case6RankingContextPerRow(unittest.TestCase):  # CANARY (subtitle) + new per-row context
    @staticmethod
    def serp(query: str, device: str, position: int) -> list[dict]:
        common = {"query": query, "device": device, "location": "Berlin,Germany", "observed_at": "2026-10-28T21:25:54Z",
                  "status": "MEASURED", "source_provider": "fixture"}
        return [dict(common, id="SERP_CURRENT_POSITION", value=position), dict(common, id="SERP_CURRENT_PAGE", value=1)]

    def test_mixed_devices_carry_device_and_date_per_row(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = scored_from(load(FIXTURE), tmp)
            report = load(scored)
            report["measurement_enrichment"] = {"metrics": self.serp("anfrage 0", "mobile", 9) + self.serp("anfrage 1", "desktop", 10)}
            dump(scored, report)
            v05 = next(v for v in build_plan(scored, tmp)["visuals"] if v["template_id"] == "V05_RANKING_POSITION")
            self.assertIn("Mobil", v05["subtitle"])
            self.assertIn("Desktop", v05["subtitle"])
            self.assertEqual([r["context_label"] for r in v05["data"]],
                             ["Berlin, Deutschland · Mobil · 28.10.2026", "Berlin, Deutschland · Desktop · 28.10.2026"])


class Case7DeclaredIconFetchFailure(unittest.TestCase):  # CANARY, fixed in a66710f
    def test_declared_icon_that_fails_to_load_is_a_fetch_problem(self) -> None:
        from attach_vibecheck03_findings import attach
        from vibecheck03 import observe
        report = copy.deepcopy(load(FIXTURE))
        report["meta"]["audit_id"] = "ebc-icon"
        html = "<html><head><title>T</title><link rel='icon' href='/icon.png'></head><body></body></html>"
        vc = observe({"run_id": "ebc-icon", "page_url": report["meta"]["audited_url"], "html": html, "html_complete": True,
                      "observed_at": "2026-10-27T10:00:00+01:00", "asset_results": {"https://example.com/icon.png": False}})
        icon = next(f for f in attach(report, vc)["findings"] if "Website-Symbol" in f.get("title", ""))
        text = " ".join(str(icon.get(k) or "") for k in ("title", "client_title", "client_observation", "client_action", "client_impact"))
        self.assertNotIn("Kein eigenes", text)
        self.assertIn("abrufbar", text)


@unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime missing: NOT RUN")
class Case8ReadyIsInvalidated(unittest.TestCase):
    built: Path
    _tmp: tempfile.TemporaryDirectory

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        scored = scored_from(load(FIXTURE), tmp)
        cls.built = tmp / "built"
        result = run("scripts/build_audit_deliverables.py", str(scored), str(cls.built), "--release-mode", "proof", "--force-svg-fallback")
        assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def bundle_copy(self, tmp: Path) -> Path:
        out = tmp / "out"
        shutil.copytree(self.built, out)
        return out

    def mark_ready(self, out: Path) -> Path:
        manifest = out / "deliverable-manifest.json"
        data = load(manifest)
        data["status"] = "CUSTOMER_RELEASE_READY"
        dump(manifest, data)
        return manifest

    def test_ready_manifest_is_downgraded_when_semantic_qa_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = self.bundle_copy(Path(td))
            manifest = self.mark_ready(out)
            qa = out / "customer_presentation.semantic-qa.json"
            q = load(qa)
            q["inspection_status"] = "FAIL"
            dump(qa, q)
            fin = run("scripts/finalize_deliverable_manifest.py", str(out))
            self.assertNotEqual(fin.returncode, 0)
            self.assertNotEqual(load(manifest)["status"], "CUSTOMER_RELEASE_READY")
            self.assertNotEqual(run("scripts/validate_deliverable_bundle.py", str(out), "--require-customer-release-ready").returncode, 0)

    def test_ready_manifest_without_pass_qa_fails_bundle_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = self.bundle_copy(Path(td))
            self.mark_ready(out)
            bundle = run("scripts/validate_deliverable_bundle.py", str(out))
            self.assertNotEqual(bundle.returncode, 0)
            self.assertIn("MANIFEST_STATUS_NOT_SUPPORTED_BY_QA", bundle.stdout + bundle.stderr)

    def test_changed_required_artifact_fails_bundle_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = self.bundle_copy(Path(td))
            quality = out / "customer-presentation-quality-report.json"
            data = load(quality)
            data["tampered_after_manifest"] = True
            dump(quality, data)
            bundle = run("scripts/validate_deliverable_bundle.py", str(out))
            self.assertNotEqual(bundle.returncode, 0)
            self.assertIn("sha256 mismatch", bundle.stdout + bundle.stderr)


GOLDEN_PAIRS = [
    # (internal wording, customer wording): simplification may shorten, never change method, origin or scope.
    ("Der wichtigste sichtbare Inhalt erscheint im mobilen Labortest spürbar verzögert.",
     "Der wichtigste sichtbare Inhalt erscheint in der mobilen Testmessung spürbar verzögert."),
    ("Im Labortest lädt die Seite langsam.", "In der Testmessung lädt die Seite langsam."),
    ("Mobile Ladezeit · synthetische Testreihe", "Mobile Ladezeit · Beispieldaten"),
    ("Synthetic fixture 1.0", "Beispieldaten 1.0"),
    ("Die mobile Labormessung bleibt in vier Testläufen über dem Zielband.",
     "Die mobile Testmessung bleibt in vier Messungen über dem Zielband."),
    ("Gilt im geprüften Umfang.", "Gilt in der Stichprobe."),
    ("Sortiert nach Belegstärke.", "Sortiert nach Belastbarkeit der Werte."),
    ("Lighthouse/PageSpeed-Labortest zeigt 3,8 s.", "technische Testmessung der Ladezeit zeigt 3,8 s."),
    # Unchanged rules that keep their meaning: pinned so a later edit cannot silently drop the evidence class.
    ("CrUX/Felddaten zeigen 3,2 s.", "reale Lade- und Nutzungsdaten zeigen 3,2 s."),
]


class GoldenPairs(unittest.TestCase):
    def test_replacements_keep_method_scope_and_evidence_class(self) -> None:
        for raw, expected in GOLDEN_PAIRS:
            self.assertEqual(clientize(raw, 200), expected, raw)

    def test_no_customer_replacement_erases_a_measurement_word(self) -> None:
        for raw in ("im mobilen Labortest", "im Labortest", "Labortest", "Labormessung", "im geprüften Umfang", "synthetische Testreihe"):
            self.assertTrue(clientize(raw, 200).strip(), raw)


if __name__ == "__main__":
    unittest.main()
