#!/usr/bin/env python3
"""Regression evals for the Strategic Relevance / customer-output guardrails patch."""
from __future__ import annotations
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
FIXTURE = ROOT / "evals" / "fixtures" / "synthetic-report.json"


def run(args: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, text=True, capture_output=True)
    if p.returncode != expect:
        raise RuntimeError(f"command rc={p.returncode} expected={expect}: {' '.join(args)}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def visible_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).casefold()


def main() -> int:
    checks: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pxk-strategic-eval-") as td:
        out = Path(td)
        scored = out / "scored-base.json"
        run([PYTHON, str(ROOT / "scripts/compute_score.py"), str(FIXTURE), str(scored)])
        base = load(scored)

        # 1) Internal PARTIAL_SCORE becomes a customer Bewertungsstand without coverage/confidence leakage.
        partial = copy.deepcopy(base)
        partial["score_summary"]["display_status"] = "PARTIAL_SCORE"
        partial["score_summary"]["label"] = "Pixelkiez Teilscore"
        partial["score_summary"]["coverage_percent"] = 72
        p_report = out / "partial.json"; p_model = out / "partial-model.json"
        write(p_report, partial)
        run([PYTHON, str(ROOT / "scripts/build_client_report_model.py"), str(p_report), str(p_model)])
        model = load(p_model)
        if model.get("cover", {}).get("score") != partial["score_summary"]["score"]:
            raise RuntimeError("PARTIAL_SCORE numeric Bewertungsstand was incorrectly hidden")
        if model.get("cover", {}).get("score_label") != "Pixelkiez Bewertungsstand":
            raise RuntimeError("PARTIAL_SCORE must use customer label Pixelkiez Bewertungsstand")
        if "teilscore" in visible_text(model) or "coverage" in visible_text(model.get("cover", {})):
            raise RuntimeError("internal partial-score metadata leaked into customer model")
        checks.append("partial_score_customer_bewertungsstand")

        # 2) An audit-process finding must never outrank actual website findings.
        process = copy.deepcopy(base)
        process_finding = {
            "id": "F-AUDIT-PROCESS",
            "severity": "critical",
            "category": "ux_conversion",
            "title": "Audit Coverage ist unvollständig",
            "metric_refs": ["UX-02"],
            "evidence": [{"id": "EV-AUDIT-PROCESS", "source": "internal"}],
            "confidence": 5,
            "client_observation": "Nur ein Teil der vorgesehenen Prüfpunkte wurde im Audit ausgeführt.",
            "client_impact": "Für die Analyse wären weitere interne Tests hilfreich.",
            "client_action": "Audit vervollständigen und interne Testabdeckung erhöhen.",
            "business_relevance": {"classification": "recommendation", "text": "Interner Prüfprozess."},
        }
        process["findings"] = [process_finding] + process.get("findings", [])
        pr = out / "process.json"; pm = out / "process-model.json"
        write(pr, process)
        run([PYTHON, str(ROOT / "scripts/build_client_report_model.py"), str(pr), str(pm)])
        pmodel = load(pm)
        ids = {x.get("id") for x in pmodel.get("findings", []) if isinstance(x, dict)}
        if "F-AUDIT-PROCESS" in ids:
            raise RuntimeError("internal audit-process finding leaked into customer levers")
        checks.append("process_finding_rejected")

        # 3) A finding backed only by not_assessed metrics must not become a customer lever.
        na = copy.deepcopy(base)
        na_metric = next((m for m in na.get("metrics", []) if isinstance(m, dict) and m.get("measurement_class") == "not_assessed"), None)
        if not na_metric:
            raise RuntimeError("fixture has no not_assessed metric")
        na_finding = {
            "id": "F-NOT-ASSESSED",
            "severity": "critical",
            "category": "performance_technology",
            "title": "Nicht gemessener Bereich",
            "metric_refs": [str(na_metric.get("id"))],
            "evidence": [{"id": "EV-NA", "source": "internal"}],
            "confidence": 5,
            "client_observation": "Dieser Bereich wurde nicht gemessen.",
            "client_impact": "Es liegen keine belastbaren Websitewerte vor.",
            "client_action": "Weitere Messungen durchführen.",
            "business_relevance": {"classification": "recommendation", "text": "Messlücke."},
        }
        na["findings"] = [na_finding] + na.get("findings", [])
        nr = out / "na.json"; nm = out / "na-model.json"
        write(nr, na)
        run([PYTHON, str(ROOT / "scripts/build_client_report_model.py"), str(nr), str(nm)])
        nmodel = load(nm)
        nids = {x.get("id") for x in nmodel.get("findings", []) if isinstance(x, dict)}
        if "F-NOT-ASSESSED" in nids:
            raise RuntimeError("not_assessed finding leaked into customer levers")
        checks.append("not_assessed_not_customer_problem")

        # 4) A validated non-core legal risk may use the separate legal evidence route.
        legal = copy.deepcopy(base)
        legal_finding = {
            "id": "F-LEGAL-ROUTE",
            "severity": "high",
            "category": "trust_privacy_content",
            "title": "Dringender rechtlicher Prüfbedarf: Betreiberangaben",
            "metric_refs": ["LEGAL-IMP-02", "LEGAL-IMP-03"],
            "evidence": [{"id": "E-990", "type": "legal_sidecar", "detail": "LEGAL-IMP-02, LEGAL-IMP-03", "method": "legal_customer_projection"}],
            "confidence": 4,
            "client_observation": "Betreiberidentität und Geschäftsanschrift waren öffentlich nicht eindeutig auffindbar.",
            "client_impact": "Je nach Sitz und Geschäftsmodell können zentrale Anbieterpflichten betroffen sein.",
            "client_action": "Betreiberangaben jetzt durch qualifizierte Rechtsberatung prüfen und korrigieren lassen.",
            "recommendation": {"action": "Betreiberangaben jetzt durch qualifizierte Rechtsberatung prüfen und korrigieren lassen.", "owner": "Website + Rechtsberatung", "horizon": "now", "acceptance_test": "Anbieterangaben erneut prüfen."},
            "business_relevance": {"classification": "inference", "text": "Vertrauens- und Rechtsprüfungsrisiko."},
            "customer_risk": {"domain": "provider_identification", "source": "impressum_compliance", "priority": "MANDATORY_CRITICAL", "claim_state": "POSSIBLE_LEGAL_REVIEW", "group": "PROVIDER_IDENTITY", "warning_label": "Dringender rechtlicher Prüfbedarf", "reason": "AUDIT_PRIORITY_CRITICAL", "legal_metric_refs": ["LEGAL-IMP-02", "LEGAL-IMP-03"]},
        }
        legal["findings"] = [legal_finding] + legal.get("findings", [])
        lr = out / "legal.json"; lm = out / "legal-model.json"
        write(lr, legal)
        run([PYTHON, str(ROOT / "scripts/build_client_report_model.py"), str(lr), str(lm)])
        lmodel = load(lm)
        if not lmodel.get("findings") or lmodel["findings"][0].get("id") != "F-LEGAL-ROUTE":
            raise RuntimeError("validated legal-sidecar risk did not pass Strategic Relevance or rank first")
        checks.append("legal_sidecar_route_customer_eligible")

        # 5) A full score remains visible, but is not repeated as a dedicated customer visual.
        fr = out / "full.json"; fm = out / "full-model.json"; vp = out / "visual-plan.json"
        write(fr, base)
        run([PYTHON, str(ROOT / "scripts/build_client_report_model.py"), str(fr), str(fm)])
        fmodel = load(fm)
        if fmodel.get("cover", {}).get("score") is None:
            raise RuntimeError("FULL_SCORE was incorrectly hidden")
        run([PYTHON, str(ROOT / "scripts/build_visualization_plan.py"), str(fr), str(vp)])
        plan = load(vp)
        selected = {x.get("template_id") for x in plan.get("visuals", []) if isinstance(x, dict)}
        if "V01_OVERALL_SCORE" in selected:
            raise RuntimeError("overall score was redundantly selected as a dedicated customer visual")
        if "V12_AUDIT_COVERAGE" in selected:
            raise RuntimeError("audit coverage visual leaked into customer plan")
        checks.append("customer_visual_score_coverage_guard")

        # 6) Internal report still preserves method/coverage transparency.
        internal_json = out / "analysis_report.json"; internal_md = out / "analysis_report.md"
        run([PYTHON, str(ROOT / "scripts/build_internal_analysis_report.py"), str(fr), str(internal_json)])
        run([PYTHON, str(ROOT / "scripts/render_internal_analysis_markdown.py"), str(internal_json), str(internal_md)])
        internal = load(internal_json)
        if len(internal.get("metrics", [])) != 48:
            raise RuntimeError("internal metric inventory no longer preserves all 48 metrics")
        internal_text = internal_md.read_text(encoding="utf-8").casefold()
        if "coverage" not in visible_text(internal) and "abdeckung" not in internal_text:
            raise RuntimeError("internal transparency layer lost coverage/method context")
        checks.append("internal_transparency_preserved")

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "baseline_release": "3.2.1-measurement-platform-integration",
        "north_star_question": "Hätte ein Unternehmer, der Geld mit seiner Seite oder dem beworbenen Service/Produkt verdient, einen strategischen Vorteil, wenn er diese Information hätte?",
        "checks": checks,
        "customer_partial_score_policy": "NUMERIC_BEWERTUNGSSTAND_NO_COVERAGE",
        "customer_process_metadata_policy": "FORBIDDEN",
        "not_assessed_customer_penalty": False,
        "customer_visual_exclusions": ["V01_OVERALL_SCORE", "V12_AUDIT_COVERAGE"],
        "internal_metric_inventory": 48,
    }
    (ROOT / "reports" / "strategic-relevance-eval-results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: strategic relevance evals -> " + ", ".join(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
