#!/usr/bin/env python3
"""Regression suite for mandatory Impressum customer-risk surfacing."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(cmd: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != expect:
        raise RuntimeError(
            f"rc={p.returncode} expected={expect}: {' '.join(cmd)}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )
    return p


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from impressum_compliance import assess_case
    from legal_customer_projection import resolve_projection

    cases = json.loads((ROOT / "evals/fixtures/impressum-compliance-cases.json").read_text(encoding="utf-8"))["cases"]
    golden = next(c for c in cases if c.get("id") == "LEG-GOLD-BFL")
    side = assess_case(golden["context"], golden["observations"], root=ROOT, discovery_scope={"complete": True})
    projection = resolve_projection(side)
    checks: list[str] = []

    if side.get("overrides", {}).get("audit_priority_critical") is not True:
        raise RuntimeError("Bo Feng Lin golden case did not produce audit_priority_critical")
    if side.get("iles", {}).get("points") != 0:
        raise RuntimeError("unresolved jurisdiction must keep ILES at zero")
    if projection.get("priority") != "MANDATORY_CRITICAL" or projection.get("required") is not True:
        raise RuntimeError("critical legal review risk was not made mandatory")
    if projection.get("claim_state") != "POSSIBLE_LEGAL_REVIEW":
        raise RuntimeError("unresolved jurisdiction must remain POSSIBLE_LEGAL_REVIEW")
    if not {"LEGAL-IMP-02", "LEGAL-IMP-03"}.issubset(set(projection.get("legal_metric_refs", []))):
        raise RuntimeError("identity/address refs missing from projection")
    checks.append("bo_feng_lin_mandatory_projection")

    with tempfile.TemporaryDirectory(prefix="pxk-legal-customer-") as td:
        t = Path(td)
        sidep = t / "impressum-compliance.json"
        write(sidep, side)
        base = ROOT / "evals/fixtures/synthetic-report.json"
        projected = t / "projected.json"
        run([PYTHON, str(ROOT / "scripts/attach_impressum_findings.py"), str(base), str(sidep), str(projected)])
        run([PYTHON, str(ROOT / "scripts/validate_report_input.py"), str(projected)])

        before_scored = t / "before-scored.json"
        after_scored = t / "after-scored.json"
        run([PYTHON, str(ROOT / "scripts/compute_score.py"), str(base), str(before_scored)])
        run([PYTHON, str(ROOT / "scripts/compute_score.py"), str(projected), str(after_scored)])
        before = json.loads(before_scored.read_text(encoding="utf-8"))["score_summary"]
        after = json.loads(after_scored.read_text(encoding="utf-8"))["score_summary"]
        for key in ("score", "display_status", "coverage_percent", "category_scores"):
            if before.get(key) != after.get(key):
                raise RuntimeError(f"legal customer patch changed core score field {key}")
        checks.append("core_score_coverage_delta_zero")

        planp = t / "visualization-plan.json"
        run([PYTHON, str(ROOT / "scripts/build_visualization_plan.py"), str(after_scored), str(planp)])
        modelp = t / "client-model.json"
        run([PYTHON, str(ROOT / "scripts/build_client_report_model.py"), str(after_scored), str(modelp), "--visual-plan", str(planp)])
        run([PYTHON, str(ROOT / "scripts/validate_client_report_model.py"), str(modelp)])
        run([PYTHON, str(ROOT / "scripts/validate_client_semantics.py"), str(modelp)])
        run([PYTHON, str(ROOT / "scripts/validate_impressum_projection.py"), str(sidep), str(after_scored), str(modelp)])
        model = json.loads(modelp.read_text(encoding="utf-8"))
        first = model.get("findings", [])[0]
        if "rechtlicher pr\u00fcfbedarf" not in str(first.get("headline", "")).casefold():
            raise RuntimeError("legal risk is not explicit in first lever headline")
        if "rechtlicher pr\u00fcfbedarf" not in str(model.get("cover", {}).get("blocker_note", "")).casefold():
            raise RuntimeError("legal risk is not explicit on cover")
        checks.append("mandatory_legal_risk_rank1_cover_roadmap_closing")
        plan = json.loads(planp.read_text(encoding="utf-8"))
        trust = next((v for v in plan.get("visuals", []) if v.get("template_id") == "V10_TRUST_MATRIX"), None)
        legal_rows = [r for r in (trust or {}).get("data", []) if "impressum" in str(r.get("signal", "")).casefold()]
        if trust is not None and (not legal_rows or any(r.get("status") != "Handlungsbedarf" for r in legal_rows)):
            raise RuntimeError("trust matrix shows the legal surface as clear while a legal customer risk is projected")
        checks.append("legal_surface_status_reconciled")

        visuals = t / "visuals"
        vreceipt = t / "visualization-render-receipt.json"
        run([PYTHON, str(ROOT / "scripts/render_visualizations.py"), str(planp), str(visuals), "--receipt", str(vreceipt), "--force-fallback"])
        pdf = t / "customer_presentation.pdf"
        html = t / "customer_presentation.html"
        preceipt = t / "presentation-render-receipt.json"
        run([PYTHON, str(ROOT / "scripts/render_diagnosis_pdf.py"), str(modelp), str(pdf), "--visual-plan", str(planp), "--visual-receipt", str(vreceipt), "--visual-dir", str(visuals), "--render-receipt", str(preceipt), "--html-out", str(html)])
        run([PYTHON, str(ROOT / "scripts/validate_pdf_output.py"), str(pdf), str(modelp)])
        run([PYTHON, str(ROOT / "scripts/validate_impressum_projection.py"), str(sidep), str(after_scored), str(modelp), str(pdf)])
        checks.append("mandatory_legal_risk_visible_in_rendered_pdf")

        omitted = copy.deepcopy(model)
        omitted["findings"] = omitted["findings"][1:]
        omitted["client_story"]["selected_lever_ids"] = omitted["client_story"]["selected_lever_ids"][1:]
        omittedp = t / "omitted.json"
        write(omittedp, omitted)
        run([PYTHON, str(ROOT / "scripts/validate_impressum_projection.py"), str(sidep), str(after_scored), str(omittedp)], expect=1)
        checks.append("omission_fails_closed")

        coverless = copy.deepcopy(model)
        coverless["cover"]["blocker_note"] = ""
        coverlessp = t / "coverless.json"
        write(coverlessp, coverless)
        run([PYTHON, str(ROOT / "scripts/validate_impressum_projection.py"), str(sidep), str(after_scored), str(coverlessp)], expect=1)
        checks.append("cover_warning_required")

        roadless = copy.deepcopy(model)
        roadless["roadmap"]["now"] = []
        roadlessp = t / "roadless.json"
        write(roadlessp, roadless)
        run([PYTHON, str(ROOT / "scripts/validate_impressum_projection.py"), str(sidep), str(after_scored), str(roadlessp)], expect=1)
        checks.append("roadmap_action_required")

        bad = t / "bad.txt"
        bad.write_text("Website ist rechtswidrig und Sie erhalten 50000 EUR Strafe.", encoding="utf-8")
        run([PYTHON, str(ROOT / "scripts/validate_customer_output_guardrails.py"), str(bad)], expect=1)
        good = t / "good.txt"
        good.write_text("Dringender rechtlicher Pr\u00fcfbedarf. Qualifizierte rechtliche Pr\u00fcfung empfohlen.", encoding="utf-8")
        run([PYTHON, str(ROOT / "scripts/validate_customer_output_guardrails.py"), str(good)])
        checks.append("anti_overclaim_preserved")

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "golden_case": "LEG-GOLD-BFL",
        "checks": checks,
        "expected_customer_priority": "MANDATORY_CRITICAL",
        "expected_claim_state": "POSSIBLE_LEGAL_REVIEW",
        "pixelkiez_score_impact": "NONE_DIRECT",
    }
    (ROOT / "reports/legal-customer-projection-eval-results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: legal customer projection evals -> " + ", ".join(checks))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
