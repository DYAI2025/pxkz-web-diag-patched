#!/usr/bin/env python3
"""Validate the Pixelkiez Website Diagnosis release gate for the visual/reporting architecture."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from semantic_release_evidence import semantic_bundle_digest


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def tree_digest(root: Path) -> str:
    return subprocess.check_output(
        [sys.executable, str(root / "scripts" / "pipeline_ledger.py"), "digest", str(root)],
        text=True,
    ).strip()


def _contract(root: Path) -> tuple[str, dict]:
    path = root / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.3.json"
    return hashlib.sha256(path.read_bytes()).hexdigest(), json.loads(path.read_text(encoding="utf-8"))


def validate_reports(root: Path, report: dict, paired: dict, semantic: dict) -> list[str]:
    """Cross-skill, paired-release and customer-semantic evidence binding (fail closed).

    A claimed PASS must be backed by digest-consistent paired evidence; a blocked
    dependency is accepted only when it is declared non-package-blocking and the
    website side passed. Customer-semantic evidence must be PASS and bound to the
    current semantic control bundle.
    """
    errors: list[str] = []
    digest, contract = _contract(root)
    version = str(contract.get("version", ""))
    cross = report.get("cross_skill_dependency") or {}
    status = cross.get("status")
    if cross.get("website_skill_side_status") != "PASS":
        errors.append("website side of batch contract not validated")
    if status == "PASS":
        if cross.get("voice_architect_side_status") != "PASS":
            errors.append("cross-skill PASS without voice-architect side PASS")
        if cross.get("shared_v1_3_sha256") != digest:
            errors.append("cross-skill shared contract digest mismatch")
        if cross.get("shared_contract_version") != version:
            errors.append("cross-skill shared contract version mismatch")
        if cross.get("website_fields") != cross.get("voice_fields"):
            errors.append("cross-skill field count mismatch")
        pc = paired.get("contract") or {}
        if paired.get("status") != "PASS":
            errors.append("paired release evidence is not PASS")
        if pc.get("sha256") != digest or pc.get("version") != version:
            errors.append("paired release evidence stale against current contract")
        if (paired.get("voice_release_harness") or {}).get("status") != "PASS":
            errors.append("paired voice harness evidence missing")
        if paired.get("truth_attack_e2e") != "PASS" or paired.get("provider_neutral_packet_e2e") != "PASS":
            errors.append("paired cross-skill E2E evidence incomplete")
    elif status != "BLOCKED_DEPENDENCY_NON_PACKAGE_BLOCKING":
        errors.append("cross-skill dependency status invalid")

    gate = report.get("customer_semantic_gate") or {}
    current = semantic_bundle_digest(root)
    if gate.get("status") != "PASS":
        errors.append("customer semantic gate is not PASS")
    if gate.get("semantic_bundle_sha256") != current:
        errors.append("customer semantic gate bound to a different semantic bundle")
    if semantic.get("status") != "PASS" or semantic.get("semantic_qa_validation") != "PASS" or semantic.get("visual_qa_validation") != "PASS":
        errors.append("customer semantic QA evidence is not PASS")
    if semantic.get("semantic_bundle_sha256") != current:
        errors.append("customer semantic QA evidence stale against current semantic bundle")
    # The semantic bundle omits rendering code (CSS, templates, plan builder), so rendered QA must also be
    # bound to the whole build-controlled tree it was inspected on.
    build = tree_digest(root)
    if semantic.get("artifact_digest") != build:
        errors.append("customer semantic QA evidence not bound to the current build artifact digest")
    if gate.get("artifact_digest") != build:
        errors.append("customer semantic gate not bound to the current build artifact digest")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_release_gate.py <skill-dir>")
    root = Path(argv[1]).resolve()
    try:
        report = json.loads((root / "reports/release-gate-report.json").read_text(encoding="utf-8"))
        visual = json.loads((root / "reports/visual-reporting-eval-results.json").read_text(encoding="utf-8"))
        gallery = json.loads((root / "reports/visualization-gallery-eval-results.json").read_text(encoding="utf-8"))
        realistic = json.loads((root / "reports/realistic-presentation-qa.json").read_text(encoding="utf-8"))
        fonts = json.loads((root / "reports/brand-font-capability.json").read_text(encoding="utf-8"))
        gateway = json.loads((root / "reports/measurement-gateway-eval-results.json").read_text(encoding="utf-8"))
        protected = json.loads((root / "reports/measurement-platform-protected-baseline.json").read_text(encoding="utf-8"))
        third_party = json.loads((root / "reports/third-party-license-ledger.json").read_text(encoding="utf-8"))
        platform_proof = json.loads((root / "reports/measurement-platform-proof.json").read_text(encoding="utf-8"))
        strategic = json.loads((root / "reports/strategic-relevance-eval-results.json").read_text(encoding="utf-8"))
        strategic_proof = json.loads((root / "reports/strategic-relevance-proof.json").read_text(encoding="utf-8"))
        v321_preservation = json.loads((root / "reports/strategic-relevance-v321-preservation.json").read_text(encoding="utf-8"))
        quality_eval = json.loads((root / "reports/customer-presentation-quality-eval-results.json").read_text(encoding="utf-8"))
        quality_proof = json.loads((root / "reports/customer-presentation-quality-proof.json").read_text(encoding="utf-8"))
        active_core = json.loads((root / "reports/core-active-eval-results.json").read_text(encoding="utf-8"))
        active_mutations = json.loads((root / "reports/core-active-mutation-test-report.json").read_text(encoding="utf-8"))
        active_score = json.loads((root / "reports/score-reconciliation-report.json").read_text(encoding="utf-8"))
        active_analysis = json.loads((root / "reports/analysis-report-reconciliation.json").read_text(encoding="utf-8"))
        active_determinism = json.loads((root / "reports/core-active-determinism-report.json").read_text(encoding="utf-8"))
        active_render = json.loads((root / "reports/active-core-render-proof.json").read_text(encoding="utf-8"))
        legal_sources = json.loads((root / "reports/impressum-legal-source-validation.json").read_text(encoding="utf-8"))
        legal_evals = json.loads((root / "reports/impressum-compliance-eval-results.json").read_text(encoding="utf-8"))
        legal_customer = json.loads((root / "reports/legal-customer-projection-eval-results.json").read_text(encoding="utf-8"))
        paired = json.loads((root / "reports/paired-release-report.json").read_text(encoding="utf-8"))
        semantic = json.loads((root / "reports/semantic-customer-qa-eval-report.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid or missing release evidence: {exc}")

    errors: list[str] = []

    # Re-run the protected Measurement Platform guard on the exact candidate.
    # A stored PASS in release-gate-report.json is not sufficient because reports/
    # is excluded from the artifact digest and may otherwise become stale.
    try:
        protection = subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_measurement_platform_baseline.py"), str(root)],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if protection.returncode != 0:
            detail = (protection.stderr or protection.stdout).strip()
            errors.append(f"measurement platform preservation live check failed: {detail}")
    except Exception as exc:
        errors.append(f"measurement platform preservation live check unavailable: {exc}")
    if report.get("release_scope") != "website-diagnosis-package": errors.append("release scope drift")
    if report.get("release_gate", {}).get("status") != "PASS": errors.append("release status is not PASS")
    if report.get("release_gate", {}).get("allowed_to_package") is not True: errors.append("allowed_to_package must be true")
    if report.get("craftsmanship_gate", {}).get("status") != "PASS": errors.append("craftsmanship gate failed")
    if report.get("anti_confabulation_gate", {}).get("status") != "PASS": errors.append("anti-confabulation gate failed")
    if report.get("anti_confabulation_gate", {}).get("blocked_claims"): errors.append("blocked_claims must be empty")
    syco = report.get("anti_sycophancy", {})
    if not isinstance(syco.get("score"), int) or syco["score"] >= syco.get("threshold", 3): errors.append("anti-sycophancy threshold failed")
    if report.get("bias_gate", {}).get("status") == "BLOCKED": errors.append("bias gate blocked")
    browser = report.get("browser_gate", {})
    if browser.get("applicable") and browser.get("status") not in {"PASS", "PASS_WITH_ASSUMPTIONS"}: errors.append("browser gate failed")
    if browser.get("blockers"): errors.append("browser blockers must be empty")

    for gate_name in (
        "batch_contract_gate", "batch_evals_gate", "core_regression_gate", "internal_report_gate",
        "active_core_gate", "active_core_render_gate",
        "visualization_reporting_gate", "weasyprint_render_gate", "brand_rendering_gate", "proof_output_gate",
        "measurement_gateway_gate", "protected_baseline_gate", "third_party_reuse_gate", "measurement_platform_proof_gate",
        "strategic_relevance_gate", "customer_output_guardrail_gate", "measurement_platform_preservation_gate",
        "customer_presentation_quality_gate",
        "impressum_legal_source_gate", "impressum_compliance_gate", "impressum_eval_gate", "impressum_customer_projection_gate",
    ):
        if report.get(gate_name, {}).get("status") != "PASS": errors.append(f"{gate_name} failed")

    if legal_sources.get("status") != "PASS": errors.append("impressum legal source validation failed")
    if legal_evals.get("status") != "PASS" or int(legal_evals.get("pass_count", 0)) != int(legal_evals.get("case_count", -1)): errors.append("impressum compliance evals failed")
    required_legal_customer = {"bo_feng_lin_mandatory_projection", "core_score_coverage_delta_zero", "mandatory_legal_risk_rank1_cover_roadmap_closing", "mandatory_legal_risk_visible_in_rendered_pdf", "omission_fails_closed", "anti_overclaim_preserved"}
    if legal_customer.get("status") != "PASS" or not required_legal_customer.issubset(set(legal_customer.get("checks") or [])):
        errors.append("impressum customer-risk projection evals failed")
    if legal_customer.get("pixelkiez_score_impact") != "NONE_DIRECT": errors.append("legal customer projection changed score firewall")
    if report.get("pixelkiez_score_impact") != "NONE_DIRECT": errors.append("legal score firewall missing")

    # Active Core Migration is additive and non-compensatory.
    if active_core.get("status") != "PASS" or active_core.get("suite") != "FULL_48_ACTIVE":
        errors.append("active core eval failed")
    for key in ("total_registry_metrics", "execution_ready", "evidence_ready", "score_admitted", "report_reconciled"):
        if active_core.get(key) != 48:
            errors.append(f"active core {key} must equal 48")
    if "synthetic evidence" not in str(active_core.get("fixture_boundary", "")).lower():
        errors.append("active core fixture boundary missing")
    if active_mutations.get("status") != "PASS" or int(active_mutations.get("detected", 0)) < 15:
        errors.append("active core mutation gate incomplete")
    if active_score.get("status") != "PASS" or active_score.get("registry_weights_unchanged") is not True or active_score.get("compute_score_changed") is not False:
        errors.append("active core score integrity failed")
    if active_score.get("fixture_only") is not True:
        errors.append("active score proof must remain fixture-only")
    if active_analysis.get("status") != "PASS" or active_analysis.get("metric_count") != 48 or active_analysis.get("weighted_contributions") != "RECONCILED":
        errors.append("active analysis reconciliation failed")
    if active_determinism.get("status") != "PASS" or active_determinism.get("semantic_digest") != active_determinism.get("shuffled_semantic_digest"):
        errors.append("active core determinism failed")
    if active_render.get("status") != "PASS" or active_render.get("renderer") != "WEASYPRINT":
        errors.append("active core rendered customer proof failed")
    if not 8 <= int(active_render.get("page_count", 0)) <= 12 or int(active_render.get("embedded_visual_count", 0)) < 4:
        errors.append("active core rendered customer proof incomplete")
    needed_active_validators = {"validate_pdf_output", "validate_presentation_brand", "validate_customer_business_language", "validate_customer_output_guardrails"}
    if not needed_active_validators.issubset(set(active_render.get("validators") or [])):
        errors.append("active core render validator coverage incomplete")
    if active_render.get("fixture_only") is not True:
        errors.append("active core render proof must remain fixture-only")

    strict = report.get("strict_customer_output_gate", {})
    exact = bool(fonts.get("exact", {}).get("display") and fonts.get("exact", {}).get("data"))
    if exact:
        if strict.get("status") != "PASS": errors.append("exact fonts available but strict customer output gate is not PASS")
    else:
        if strict.get("status") != "BLOCKED_EXTERNAL_FONT": errors.append("missing exact fonts must block strict customer output")
        if strict.get("customer_release_ready") is not False: errors.append("missing exact fonts cannot be customer-release-ready")
    if report.get("brand_rendering_gate", {}).get("font_binary_policy") != "NOT_BUNDLED": errors.append("font binaries must not be bundled")
    if report.get("brand_rendering_gate", {}).get("strict_customer_mode_fail_closed") is not True: errors.append("strict customer font gate must fail closed")

    if visual.get("status") != "PASS" or visual.get("metric_count") != 48: errors.append("visual/reporting architecture eval incomplete")
    if visual.get("mandatory_product_outputs") != ["analysis_report.json", "analysis_report.md", "customer_presentation.pdf"]: errors.append("mandatory output contract drift")
    if not 5 <= int(visual.get("selected_visual_count", 0)) <= 7: errors.append("visual architecture eval must select 5-7 visuals")
    if visual.get("renderer") != "WEASYPRINT": errors.append("WeasyPrint was not validated as customer renderer")
    if visual.get("benchmark_without_context") != "BLOCKED" or visual.get("ranking_without_context") != "BLOCKED": errors.append("fake benchmark/ranking negative controls failed")
    if visual.get("unsafe_svg") != "REJECTED": errors.append("unsafe SVG negative control failed")

    if gallery.get("status") != "PASS" or gallery.get("vega_lite_templates") != 14 or gallery.get("rendered_count") != 15:
        errors.append("approved visualization gallery incomplete")
    if realistic.get("status") != "PASS" or not 8 <= int(realistic.get("page_count", 0)) <= 12 or not 4 <= int(realistic.get("selected_visual_count", 0)) <= 7:
        errors.append("realistic rendered presentation QA incomplete")
    if realistic.get("visual_qa") != "PASS" or realistic.get("semantic_qa") != "PASS": errors.append("realistic rendered QA did not pass")
    if realistic.get("internal_metric_count") != 48: errors.append("realistic internal report is not complete")
    if realistic.get("customer_release_ready") is not False and not exact: errors.append("realistic proof incorrectly claims exact-font customer release")
    selected_templates = set(realistic.get("selected_template_ids") or [])
    if selected_templates & {"V01_OVERALL_SCORE", "V12_AUDIT_COVERAGE"}:
        errors.append("customer proof selected forbidden score/coverage visual")


    if gateway.get("status") != "PASS" or gateway.get("core_metric_count") != 48:
        errors.append("measurement gateway integration eval incomplete")
    if gateway.get("scoring_policy") != "NON_SCORING_ENRICHMENT":
        errors.append("measurement gateway must remain non-scoring enrichment")
    if protected.get("baseline_tree_digest") != report.get("measurement_platform_baseline_digest"):
        errors.append("measurement platform baseline digest mismatch")
    protected_files = protected.get("protected_files")
    if not isinstance(protected_files, list) or len(protected_files) < 40:
        errors.append("protected baseline manifest incomplete")
    repos = third_party.get("repositories")
    if not isinstance(repos, list) or len(repos) != 4 or any(item.get("source_code_copied") is not False for item in repos if isinstance(item, dict)):
        errors.append("third-party no-copy gate failed")
    if platform_proof.get("status") != "PASS":
        errors.append("measurement platform proof status failed")
    if platform_proof.get("renderer") != "WEASYPRINT" or platform_proof.get("page_count") != 12 or platform_proof.get("selected_visual_count") != 7:
        errors.append("measurement platform rendered proof incomplete")
    if platform_proof.get("pdf_output") != "PASS" or platform_proof.get("pdf_brand") != "PASS" or platform_proof.get("customer_language") != "PASS":
        errors.append("measurement platform PDF proof validators failed")
    if platform_proof.get("protected_customer_closing") is not True or platform_proof.get("protected_visual_catalog") is not True:
        errors.append("protected presentation invariants not preserved")
    if strategic.get("status") != "PASS" or strategic.get("internal_metric_inventory") != 48:
        errors.append("strategic relevance regression incomplete")
    required_strategic = {"partial_score_customer_bewertungsstand", "process_finding_rejected", "not_assessed_not_customer_problem", "legal_sidecar_route_customer_eligible", "customer_visual_score_coverage_guard", "internal_transparency_preserved"}
    if not required_strategic.issubset(set(strategic.get("checks") or [])):
        errors.append("strategic relevance required checks incomplete")
    if quality_eval.get("status") != "PASS":
        errors.append("customer presentation quality regression failed")
    if quality_proof.get("status") != "PASS" or quality_proof.get("final_state", {}).get("quality_status") != "PASS":
        errors.append("customer presentation quality rendered proof failed")
    if quality_proof.get("initial_state", {}).get("quality_status") != "PENDING_QA" or quality_proof.get("initial_state", {}).get("delivery_allowed") is not False:
        errors.append("quality proof does not demonstrate fail-closed PENDING_QA draft state")
    if quality_proof.get("observed_repair_loop", {}).get("rerender_required") is not True or quality_proof.get("observed_repair_loop", {}).get("all_pages_reinspected_after_repair") is not True:
        errors.append("quality proof does not demonstrate repair/rerender/reinspection loop")
    required_quality = {"partial_score_as_bewertungsstand", "ordinal_priority_no_fake_magnitude", "privacy_overclaim_rejected", "closing_action_fragment_rejected", "four_lever_business_impact_rendered"}
    if not required_quality.issubset(set(quality_eval.get("checks") or [])):
        errors.append("customer presentation quality required checks incomplete")
    if report.get("visual_story_gate", {}).get("customer_score_policy") != "FULL_SCORE_OR_PARTIAL_BEWERTUNGSSTAND":
        errors.append("customer score projection policy not reconciled")
    if strategic_proof.get("status") != "PASS" or strategic_proof.get("guardrails") != "PASS":
        errors.append("strategic customer proof failed")
    if strategic_proof.get("visual_qa") != "PASS" or strategic_proof.get("semantic_qa") != "PASS":
        errors.append("strategic proof rendered QA failed")
    if strategic_proof.get("top_lever_count") != 4 or not 4 <= int(strategic_proof.get("selected_visual_count", 0)) <= 7:
        errors.append("strategic proof story contract failed")
    if strategic_proof.get("internal_metric_count") != 48:
        errors.append("strategic proof internal metric inventory incomplete")
    if int(strategic_proof.get("measurement_enrichment_metric_count", 0)) < 1:
        errors.append("combined strategic/measurement proof missing enrichment")
    if v321_preservation.get("status") != "PASS" or v321_preservation.get("baseline_tree_digest") != "f9663c8c616f1c6ea1be95098eb6c27065f2018e4f8fe47499059cca93e637f6":
        errors.append("v3.2.1 merge preservation evidence failed")
    if v321_preservation.get("deleted_files"):
        errors.append("v3.2.1 merge unexpectedly deletes baseline files")
    live = report.get("measurement_gateway_live_gate", {})
    if live.get("status") not in {"PASS", "NOT_ASSESSED_NON_BLOCKING"}:
        errors.append("measurement gateway live gate status invalid")
    if live.get("package_blocking") is not False:
        errors.append("optional live gateway verification must be explicitly non-package-blocking")

    try:
        errors.extend(validate_reports(root, report, paired, semantic))
    except Exception as exc:
        errors.append(f"cross-skill/semantic evidence unavailable: {exc}")

    try:
        current = tree_digest(root)
        if report.get("artifact_digest") != current: errors.append(f"release report artifact digest stale: {report.get('artifact_digest')} != {current}")
    except Exception as exc:
        errors.append(f"artifact digest unavailable: {exc}")

    if errors:
        return fail("; ".join(errors))
    print("PASS: release gate visual/reporting architecture + customer quality gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
