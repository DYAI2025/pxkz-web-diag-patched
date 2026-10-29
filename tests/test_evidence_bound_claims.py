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

    def model_meta(self, fixture: Path) -> dict:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored, model = scored_from(load(fixture), tmp), tmp / "model.json"
            result = run("scripts/build_client_report_model.py", str(scored), str(model))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return load(model)["meta"]

    def test_example_data_is_announced_in_the_model(self) -> None:
        self.assertEqual(self.model_meta(FIXTURE).get("sample_data_notice"), "Beispieldaten, keine Live-Messung")

    def test_lab_measurements_carry_no_example_data_notice(self) -> None:
        # Every metric of this fixture reads as a lab measurement, none as example data.
        self.assertNotIn("sample_data_notice", self.model_meta(ROOT / "evals/fixtures/baumdienst-renner-reflection-regression.json"))

    def test_real_data_template_keeps_its_sampling_basis(self) -> None:
        """Rendered with the renderer's StrictUndefined environment, a model without the notice keeps the sampling sentence."""
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored, model_path = scored_from(load(ROOT / "evals/fixtures/baumdienst-renner-reflection-regression.json"), tmp), tmp / "model.json"
            self.assertEqual(run("scripts/build_client_report_model.py", str(scored), str(model_path)).returncode, 0)
            model = load(model_path)
        self.assertNotIn("sample_data_notice", model["meta"])
        env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), undefined=StrictUndefined, autoescape=True)
        html = env.get_template("presentation.html.j2").render(model=model, visuals=[], findings=model["findings"][:4], css="", font_status="EXACT")
        self.assertIn("Grundlage: Stichprobe öffentlich erreichbarer Seiten", html)
        self.assertNotIn("Beispieldaten", html)

    @unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime missing: NOT RUN")
    def test_every_proof_page_names_example_data(self) -> None:
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = scored_from(load(FIXTURE), tmp)
            result = run("scripts/build_audit_deliverables.py", str(scored), str(tmp / "out"), "--release-mode", "proof", "--force-svg-fallback")
            self.assertEqual(result.returncode, 0, result.stdout[-1500:] + result.stderr[-1500:])
            pages = [page.extract_text() or "" for page in PdfReader(str(tmp / "out" / "customer_presentation.pdf")).pages]
            missing = [i + 1 for i, text in enumerate(pages) if "Beispieldaten" not in text]
            self.assertEqual(missing, [], "pages without an example-data notice")
            self.assertNotIn("Stichprobe öffentlich erreichbarer Seiten", "\n".join(pages))


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

    def test_fixture_replay_rankings_are_example_data_without_a_measurement_date(self) -> None:
        import re
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = scored_from(load(FIXTURE), tmp)
            report = load(scored)
            metrics = self.serp("anfrage 0", "mobile", 9) + self.serp("anfrage 1", "desktop", 10)
            for m in metrics:
                m["source_type"] = "FIXTURE_REPLAY"
            report["measurement_enrichment"] = {"mode": "FIXTURE", "metrics": metrics}
            dump(scored, report)
            v05 = next(v for v in build_plan(scored, tmp)["visuals"] if v["template_id"] == "V05_RANKING_POSITION")
            self.assertEqual(v05.get("evidence_method"), "SYNTHETIC")
            self.assertIn("Beispieldaten", v05["subtitle"])
            labels = [r["context_label"] for r in v05["data"]] + [v05["subtitle"]]
            self.assertEqual([x for x in labels if re.search(r"\d{2}\.\d{2}\.\d{4}", x)], [], "a replay time is not a measurement date")
            self.assertTrue(all("Beispieldaten" in x for x in labels), labels)

    @unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime missing: NOT RUN")
    def test_example_data_enrichment_blocks_customer_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored, enrichment, enriched = scored_from(load(FIXTURE), tmp), tmp / "enrichment.json", tmp / "enriched.json"
            collected = run("scripts/collect_measurement_enrichment.py", "https://example.com", str(enrichment),
                            "--config", "evals/fixtures/measurement-enrichment-config.json",
                            "--fixture-bundle", "evals/fixtures/measurement-provider-responses.json", "--offline")
            self.assertEqual(collected.returncode, 0, collected.stdout + collected.stderr)
            self.assertEqual(run("scripts/attach_measurement_enrichment.py", str(scored), str(enrichment), str(enriched)).returncode, 0)
            result = run("scripts/build_audit_deliverables.py", str(enriched), str(tmp / "out"), "--release-mode", "customer", "--force-svg-fallback")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MEASUREMENT_ENRICHMENT", result.stdout + result.stderr)
            self.assertFalse((tmp / "out" / "customer_presentation.pdf").exists())

    def test_per_row_context_stays_legible_in_the_rendered_svg(self) -> None:
        """The per-row context line obeys the 13 px SVG floor of validate_visual_assets.py and stays above the footer."""
        import re
        from svg_chart_renderer import render_svg
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = scored_from(load(FIXTURE), tmp)
            report = load(scored)
            metrics = []
            for i in range(8):
                metrics += self.serp(f"anfrage {i}", "mobile" if i % 2 else "desktop", 3 + i)
            report["measurement_enrichment"] = {"metrics": metrics}
            dump(scored, report)
            v05 = next(v for v in build_plan(scored, tmp)["visuals"] if v["template_id"] == "V05_RANKING_POSITION")
            svg = render_svg(v05)
            sizes = [float(x) for x in re.findall(r'font-size="([0-9.]+)"', svg)]
            self.assertGreaterEqual(min(sizes), 13, sizes)
            self.assertIn("Berlin, Deutschland · Desktop · 28.10.2026", svg)
            ys = [float(y) for y in re.findall(r'<text x="42" y="([0-9.]+)"', svg)]
            self.assertLess(max(ys), 407, "row text must stay above the footer rule")


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


class ReviewRoundOne(unittest.TestCase):
    """Defects an independent adversarial review found on the nine fresh proof PDFs of 6846366."""

    def model_for(self, report: dict, tmp: Path) -> dict:
        scored, model = scored_from(report, tmp), tmp / "model.json"
        result = run("scripts/build_client_report_model.py", str(scored), str(model))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return load(model)

    def render_template(self, model: dict) -> str:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined
        env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), undefined=StrictUndefined, autoescape=True)
        return env.get_template("presentation.html.j2").render(model=model, visuals=[], findings=model["findings"][:4], css="", font_status="EXACT")

    def test_example_enrichment_highlights_do_not_claim_real_usage(self) -> None:  # F1
        import re
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored, enrichment, enriched, model = scored_from(load(FIXTURE), tmp), tmp / "e.json", tmp / "enriched.json", tmp / "m.json"
            self.assertEqual(run("scripts/collect_measurement_enrichment.py", "https://example.com", str(enrichment), "--config",
                                 "evals/fixtures/measurement-enrichment-config.json", "--fixture-bundle",
                                 "evals/fixtures/measurement-provider-responses.json", "--offline").returncode, 0)
            self.assertEqual(run("scripts/attach_measurement_enrichment.py", str(scored), str(enrichment), str(enriched)).returncode, 0)
            self.assertEqual(run("scripts/build_client_report_model.py", str(enriched), str(model)).returncode, 0)
            highlights = load(model)["closing"]["measurement_highlights"]
        self.assertEqual(len(highlights), 3)
        text = " ".join(f"{h['label']} {h['value']} {h['context']}" for h in highlights)
        self.assertNotIn("Reale", text)
        self.assertNotIn("dokumentiert", text)
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", text), text)
        self.assertNotIn("Ladezeit", text, "an LCP p75 value is not a load time")
        self.assertTrue(all("Beispieldaten" in h["context"] for h in highlights), highlights)

    def test_roadmap_keeps_audit_priorities_and_one_execution_order(self) -> None:  # F2, F3
        from build_client_report_model import short_action
        with tempfile.TemporaryDirectory() as td:
            model = self.model_for(load(FIXTURE), Path(td))
        # Audit roadmap: F-003 now/P1, F-001 and F-002 0-30 days/P1, F-004 31-90 days/P2.
        self.assertEqual([[i["priority"] for i in model["roadmap"][k]] for k in ("now", "next_30_days", "next_quarter")],
                         [["P1"], ["P1", "P1"], ["P2"]])
        by_id = {f["id"]: f for f in model["findings"]}
        order = ["F-003", "F-001", "F-002", "F-004"]
        self.assertEqual(model["closing"]["actions"], [short_action(by_id[x]["action"]) for x in order])
        self.assertEqual(model["recommendation"]["next_step"], model["roadmap"]["now"][0]["action"])

    def test_matrix_cap_comes_only_from_customer_levers(self) -> None:  # F5
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            report = load(FIXTURE)
            set_metric(report, "AI-05", score=100, status="strong")  # cited only by F-005, which is not a customer lever
            plan = build_plan(scored_from(report, tmp), tmp)
        self.assertNotIn("F-005", plan["top_levers"])
        v08 = next(v for v in plan["visuals"] if v["template_id"] == "V08_AI_ANSWERABILITY")
        self.assertEqual(next(r["status"] for r in v08["data"] if r["metric_ref"] == "AI-05"), "Klar")

    def legal_report(self) -> dict:
        from attach_impressum_findings import finding_from
        from impressum_compliance import assess_case
        report = load(FIXTURE)
        golden = next(c for c in load(ROOT / "evals/fixtures/impressum-compliance-cases.json")["cases"] if c.get("id") == "LEG-GOLD-BFL")
        report["findings"].append(finding_from(assess_case(golden["context"], golden["observations"], root=ROOT, discovery_scope={"complete": True}), 99))
        return report

    def test_category_bars_do_not_vouch_for_an_area_under_legal_review(self) -> None:  # F6
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            legal = build_plan(scored_from(self.legal_report(), tmp, "legal"), tmp)
            plain = build_plan(scored_from(load(FIXTURE), tmp, "plain"), tmp)
        bars = lambda plan: [r["label"] for v in plan["visuals"] if v["template_id"] == "V02_CATEGORY_BARS" for r in v["data"]]
        self.assertTrue(any(x.startswith("Vertrauen") for x in bars(plain)), bars(plain))
        self.assertFalse(any(x.startswith("Vertrauen") for x in bars(legal)), bars(legal))

    def test_empty_strengths_leave_no_empty_column(self) -> None:  # F9
        with tempfile.TemporaryDirectory() as td:
            model = self.model_for(load(FIXTURE), Path(td))
        model["executive"]["strengths"] = []
        html = self.render_template(model)
        self.assertNotIn('<div class="label">Stärken</div>', html)
        # The remaining priorities column takes the full width instead of leaving half the card empty.
        self.assertIn('class="summary-columns single"', html)

    def test_example_data_page_two_footer_carries_no_report_date(self) -> None:  # P1
        with tempfile.TemporaryDirectory() as td:
            model = self.model_for(load(FIXTURE), Path(td))
        self.assertIn("sample_data_notice", model["meta"])
        self.assertNotIn(f"Beispieldaten · {model['meta']['date']}", self.render_template(model))

    def test_threshold_value_carries_unit_and_german_decimal(self) -> None:  # F10
        from svg_chart_renderer import render_svg
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            v07 = next(v for v in build_plan(scored_from(load(FIXTURE), tmp), tmp)["visuals"] if v["template_id"] == "V07_PERFORMANCE_THRESHOLD")
        self.assertNotIn("Ladezeit", v07["subtitle"])
        svg = render_svg(v07)
        self.assertIn("3,8 s", svg)
        self.assertIn("Ziel ≤ 2,5 s", svg)
        self.assertNotIn("3.8", svg)

    def test_ranking_chart_names_its_position_scale(self) -> None:  # F11
        from svg_chart_renderer import render_svg
        visual = {"id": "VIZ-001", "template_id": "V05_RANKING_POSITION", "title": "Google-Positionen nach Suchanfrage", "subtitle": "x",
                  "data": [{"query": "a", "position": 18}, {"query": "b", "position": 9}]}
        svg = render_svg(visual)
        self.assertIn("Position 1", svg)
        self.assertIn("Position 18", svg)

    def test_orange_page_text_meets_contrast_minimum(self) -> None:  # F8
        import re
        css = (ROOT / "assets/presentation.css").read_text(encoding="utf-8")

        def colour(selector: str, fallback: str) -> str:
            m = re.search(re.escape(selector) + r"[^{]*\{[^}]*?color:\s*(#[0-9A-Fa-f]{6})", css)
            if m:
                return m.group(1)
            return re.search(re.escape(fallback) + r"\s*\{[^}]*?color:\s*(#[0-9A-Fa-f]{6})", css).group(1)

        def lum(hexcode: str) -> float:
            c = [int(hexcode[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

        def ratio(a: str, b: str) -> float:
            hi, lo = sorted((lum(a), lum(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)

        for selector, fallback in ((".page.orange .footer", ".footer"), (".page.orange .section-title p", ".section-title p")):
            self.assertGreaterEqual(ratio(colour(selector, fallback), "#EC5E43"), 4.5, selector)


class ReviewRoundTwo(ReviewRoundOne):
    """Defects the second independent adversarial review found on the nine proof PDFs of 9c506de."""

    def test_mandatory_critical_legal_lever_is_not_sold_as_high(self) -> None:  # R04
        with tempfile.TemporaryDirectory() as td:
            model = self.model_for(self.legal_report(), Path(td))
        legal = model["findings"][0]
        self.assertEqual(legal["severity"], "critical", legal["headline"])

    def test_https_row_does_not_vouch_for_security_headers(self) -> None:  # R07
        from client_story import clientize
        self.assertEqual(clientize("HTTPS & sichtbare Security-Header", 80), "HTTPS-Verschlüsselung")

    def test_lcp_action_keeps_check_and_remeasure(self) -> None:  # R12
        from client_story import clientize
        text = clientize("LCP-Element, Bildauslieferung und kritische Ressourcen prüfen und danach erneut messen.", 125)
        self.assertIn("erneut messen", text)
        self.assertNotIn("beschleunigen", text, "the audit asks to check and re-measure, it does not name images as the cause")

    def test_titles_promise_no_strengths_when_none_are_shown(self) -> None:  # R14
        with tempfile.TemporaryDirectory() as td:
            model = self.model_for(self.legal_report(), Path(td))
        self.assertEqual(model["executive"]["strengths"], [])
        self.assertNotIn("gut macht", model["cover"]["title"])
        self.assertNotIn("Was heute trägt", self.render_template(model))

    def test_field_highlight_reads_as_visits_without_jargon(self) -> None:  # R09, R18
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored, enrichment, enriched, model = scored_from(load(FIXTURE), tmp), tmp / "e.json", tmp / "enriched.json", tmp / "m.json"
            self.assertEqual(run("scripts/collect_measurement_enrichment.py", "https://example.com", str(enrichment), "--config",
                                 "evals/fixtures/measurement-enrichment-config.json", "--fixture-bundle",
                                 "evals/fixtures/measurement-provider-responses.json", "--offline").returncode, 0)
            self.assertEqual(run("scripts/attach_measurement_enrichment.py", str(scored), str(enrichment), str(enriched)).returncode, 0)
            self.assertEqual(run("scripts/build_client_report_model.py", str(enriched), str(model)).returncode, 0)
            card = next(h for h in load(model)["closing"]["measurement_highlights"] if "Hauptinhalt" in h["value"])
        self.assertNotIn("p75", card["value"])
        self.assertIn("3 von 4 Besuchen", card["value"], "visitor data must read differently from the lab test measurement")

    def test_sage_page_text_meets_contrast_minimum(self) -> None:  # R15
        import re
        css = (ROOT / "assets/presentation.css").read_text(encoding="utf-8")
        sage = re.search(r"^\.page \{[^}]*background:\s*(#[0-9A-Fa-f]{6})", css, re.M).group(1)
        for selector in (".footer", ".section-title p"):
            colour = re.search(r"^" + re.escape(selector) + r"\s*\{[^}]*?color:\s*(#[0-9A-Fa-f]{6})", css, re.M).group(1)
            lum = lambda h: (lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])(
                [(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4) for x in (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))])
            hi, lo = sorted((lum(colour), lum(sage)), reverse=True)
            self.assertGreaterEqual((hi + 0.05) / (lo + 0.05), 4.5, selector)

    def test_ranking_axis_ends_match_their_labels(self) -> None:  # R16
        import re
        from svg_chart_renderer import render_svg
        svg = render_svg({"id": "VIZ-001", "template_id": "V05_RANKING_POSITION", "title": "t", "subtitle": "s",
                          "data": [{"query": "a", "position": 18}, {"query": "b", "position": 1}]})
        xs = [float(x) for x in re.findall(r'<circle cx="([0-9.]+)"', svg)]
        self.assertEqual(xs, [340.0, 810.0])


ACTIVE_FINDINGS = ROOT / "evals/fixtures/active-positive-consistent-findings.v1.json"


def active_positive_scored(tmp: Path) -> Path:
    """The active-positive release case: consistent findings on the full-48 fixture execution (example data)."""
    report, fx = load(FIXTURE), load(ACTIVE_FINDINGS)
    for key in ("findings", "roadmap", "executive_summary"):
        report[key] = fx[key]
    src, mat = tmp / "active.input.json", tmp / "active.materialized.json"
    dump(src, report)
    result = run("scripts/materialize_core_metrics.py", str(ROOT), str(src), "evals/fixtures/full-48-core-execution.json", str(mat),
                 "--admission-out", str(tmp / "active.admission.json"))
    assert result.returncode == 0, result.stdout + result.stderr
    return scored_from(load(mat), tmp, "active")


class ReviewRoundThree(ReviewRoundOne):
    """Owner decisions on the second independent review (2026-10-29): lever contradiction rule, visual admission,
    presence wording for legal rows, two named orders, consistent active-positive input."""

    def rows(self, plan: dict, template: str) -> dict[str, dict]:
        return {r["metric_ref"]: r for v in plan["visuals"] if v["template_id"] == template for r in v["data"]}

    def test_lever_is_rejected_when_its_primary_metric_reads_clear(self) -> None:  # R01
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            report = load(FIXTURE)
            set_metric(report, "UX-02", score=100, status="strong")  # F-001 cites UX-02 first
            plan = build_plan(scored_from(report, tmp), tmp)
        self.assertNotIn("F-001", plan["top_levers"])
        self.assertEqual(len(plan["top_levers"]), 4)

    def test_threshold_page_only_illustrates_a_lever(self) -> None:  # R10, R11
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            legal = build_plan(scored_from(self.legal_report(), tmp, "legal"), tmp)
            plain = build_plan(scored_from(load(FIXTURE), tmp, "plain"), tmp)
        has_v07 = lambda plan: any(v["template_id"] == "V07_PERFORMANCE_THRESHOLD" for v in plan["visuals"])
        self.assertIn("F-002", plain["top_levers"])
        self.assertTrue(has_v07(plain))
        self.assertNotIn("F-002", legal["top_levers"])
        self.assertFalse(has_v07(legal))

    def test_presence_rows_read_as_present_not_clear(self) -> None:  # R06
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            rows = self.rows(build_plan(scored_from(load(FIXTURE), tmp), tmp), "V10_TRUST_MATRIX")
        for mid in ("TRUST-01", "TRUST-02"):
            self.assertEqual(rows[mid]["status"], "Nicht belastbar bewertet", mid)
            self.assertTrue(rows[mid]["signal"].endswith("(vorhanden)"), rows[mid]["signal"])

    def test_legal_contested_rows_are_not_assessed(self) -> None:  # R05
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plan = build_plan(scored_from(self.legal_report(), tmp), tmp)
        v10 = self.rows(plan, "V10_TRUST_MATRIX")
        for mid in ("TRUST-01", "TRUST-04", "TRUST-07"):
            if mid in v10:
                self.assertEqual(v10[mid]["status"], "Nicht belastbar bewertet", mid)
        self.assertIn("TRUST-01", v10)
        v08 = self.rows(plan, "V08_AI_ANSWERABILITY")
        self.assertFalse({"AI-01", "AI-06"} & set(v08), "the value-tinted matrix has no neutral state; contested rows stay out")

    def test_lever_order_and_execution_order_are_named(self) -> None:  # R03
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plan = build_plan(scored_from(load(FIXTURE), tmp), tmp)
            model = self.model_for(load(FIXTURE), tmp)
        v03 = next(v for v in plan["visuals"] if v["template_id"] == "V03_TOP_LEVERS")
        self.assertNotIn("Dringlichkeit", v03["subtitle"])
        self.assertIn("Bedeutung", v03["subtitle"])
        html = self.render_template(model)
        self.assertNotIn("WAS WIR JETZT TUN", html)
        self.assertIn("REIHENFOLGE DER UMSETZUNG", html)
        self.assertIn("Nach geschäftlicher Bedeutung geordnet", html)

    def test_cover_warns_when_a_lever_is_critical(self) -> None:  # R13
        report = load(FIXTURE)
        for f in report["findings"]:
            if f["id"] in {"F-001", "F-003"}:
                f["severity"] = "critical"
        with tempfile.TemporaryDirectory() as td:
            model = self.model_for(report, Path(td))
        self.assertTrue(model["cover"]["blocker_note"])

    def test_active_positive_findings_match_their_metrics(self) -> None:  # R01, R02
        from customer_status import customer_status
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            scored = active_positive_scored(tmp)
            report = load(scored)
            plan = build_plan(scored, tmp)
        metrics = {m["id"]: m for m in report["metrics"]}
        self.assertEqual(len(plan["top_levers"]), 4)
        for f in report["findings"]:
            cited = [metrics[x] for x in f["metric_refs"]]
            states = {customer_status(m)["key"] for m in cited}
            if f["severity"] == "positive":
                self.assertEqual(states, {"CLEAR"}, f["id"])
            else:
                self.assertNotEqual(customer_status(cited[0])["key"], "CLEAR", f["id"])
            ev_ids = {e["id"] for e in f["evidence"]}
            self.assertTrue(ev_ids <= {r for m in cited for r in m.get("evidence_refs", [])}, f["id"])


class MutationCanary(unittest.TestCase):
    """The claim eval must go red when the lab-to-device rewrite returns: proves the gate can fail."""

    def test_eval_fails_on_reintroduced_lab_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "pixelkiez-website-diagnosis"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "reports", "dist", "__pycache__", ".pytest_cache", "inputs"))
            story = root / "scripts/client_story.py"
            text = story.read_text(encoding="utf-8")
            mutated = text.replace('_keep_case("in der mobilen Testmessung")', '"auf Mobilgeräten"', 1)
            self.assertNotEqual(text, mutated, "mutation target must exist")
            story.write_text(mutated, encoding="utf-8")
            # Cut this canary out of the copied suite so the inner run cannot recurse.
            suite = root / "tests/test_evidence_bound_claims.py"
            body = suite.read_text(encoding="utf-8")
            cut = body.index("class MutationCanary(unittest.TestCase):")
            suite.write_text(body[:cut] + 'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
            out = Path(td) / "eval.json"
            result = run("scripts/run_evidence_bound_claim_evals.py", str(root), "--json-out", str(out), cwd=root)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            report = load(out)
            self.assertEqual(report["status"], "FAIL")
            self.assertGreaterEqual(report["failures"], 1)
            failed = {r["test"] for r in report["results"] if r["outcome"] == "FAIL"}
            self.assertIn("tests.test_evidence_bound_claims.Case1LabStaysLab.test_mobile_lab_sentence_is_not_rewritten_to_real_mobile", failed)

if __name__ == "__main__":
    unittest.main()
