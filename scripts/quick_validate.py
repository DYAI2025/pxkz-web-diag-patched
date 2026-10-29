#!/usr/bin/env python3
"""Validate the complete Pixelkiez Website Diagnosis skill structure."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_NAMES = {"render_diagnosis_pptx.mjs", "validate_pptx_output.py", "client-presentation.schema.json"}

BASE_REQUIRED = [
    "README.md", "SKILL.md", "agents/openai.yaml", "requirements.txt",
    "assets/brand.json", "assets/brand-tokens.json", "assets/measurement-registry.json", "assets/branch-priority-profiles.v1.json", "schemas/branch-priority.schema.json", "scripts/branch_priority.py", "scripts/build_boundary.py", "references/branch-aware-customer-prioritization.md", "tests/test_branch_priority.py", "scripts/vibecheck03.py", "scripts/vibecheck03_admission.py", "scripts/attach_vibecheck03_findings.py", "schemas/vibecheck03-diagnostics.schema.json", "assets/vibecheck03.check-catalog.v1.json", "assets/vibecheck03-customer-admission-rules.v1.json", "references/vibecheck03-diagnostics.md", "tests/test_vibecheck03.py", "tests/test_vibecheck03_admission.py", "tests/test_priority_pipeline.py", "tests/test_legacy_oracles.py", "evals/fixtures/golden/legacy-oracles.v1.json", "evals/fixtures/branch-priority-tie-report.SYNTHETIC.json", "scripts/run_branch_priority_evals.py", "scripts/run_vc03_customer_release_evals.py", "scripts/evidence_method_labels.py", "scripts/validate_customer_claim_bindings.py", "scripts/run_evidence_bound_claim_evals.py", "scripts/run_customer_release_cases.py", "tests/test_evidence_bound_claims.py", "assets/capability-registry.json", "assets/enrichment-metric-registry.json", "assets/core-evidence-bindings.active.v1.json",
    "assets/sql/ga4_journey_events.sql",
    "assets/PXK_web_audit_template.pdf", "assets/presentation.css", "assets/vega-lite-schema-v6.4.3.json",
    "assets/third-party/README.md", "assets/third-party/vega-lite-LICENSE.txt",
    "assets/fonts/font-manifest.json", "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf",
    "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf", "assets/fonts/schibsted-grotesk/OFL.txt",
    "assets/fonts/schibsted-grotesk/AUTHORS.txt", "assets/fonts/ibm-plex-mono/IBMPlexMono-Regular.ttf",
    "assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf", "assets/fonts/ibm-plex-mono/LICENSE.txt",
    "tests/test_packaged_brand_fonts.py", "tests/test_customer_claim_scope.py", "tests/test_capability_execution_note.py",
    "assets/brand/colors.css", "assets/brand/typography.css", "assets/brand/spacing.css",
    "assets/brand/document.css", "assets/brand/brand-devices.css", "assets/brand/report-structure.html",
    "references/audit-method.md", "references/measurement-contract.md", "references/scoring-policy.md",
    "references/pdf-report-contract.md", "references/brand-design-system.md", "references/brand-rendering-contract-v2.md",
    "references/chart-template-contract.md", "references/client-storytelling-contract.md", "references/semantic-customer-story-policy.md",
    "references/visualization-and-reporting-architecture-v1.md", "references/visualization-template-catalog-v2.md",
    "references/internal-analysis-report-contract.md", "references/business-visualization-system.md", "references/pixelkiez-brand-rendering-contract.md", "references/upstream-visualization-source-notes.md",
    "references/third-party-notices.md", "references/licenses/vega-lite-BSD-3-Clause.txt",
    "references/elevenlabs-batch-export.md", "references/batch-contract-migration-and-rollback.md",
    "references/parallel-audit-reconciliation.md", "references/future-scenarios.md",
    "references/source-policy.md", "references/source-map.md", "references/security-and-tools.md",
    "references/eval-design.md", "references/release-gate-policy.md", "references/installability-and-distribution.md", "references/customer-presentation-quality-contract.md",
    "references/agent-agnostic-compatibility.md", "references/capability-parity-policy.md",
    "references/enterprise-skill-output-evaluator.md", "references/pipeline-ledger.md",
    "references/measurement-enrichment-contract.md", "references/customer-warning-semiotics.md", "references/strategic-relevance-customer-output-contract.md",
    "references/impressum-compliance-method.md", "references/impressum-legal-source-map.md",
    "references/measurement-gateway-contract.md", "references/core-active-measurement-migration.md", "references/third-party-capability-source-map.md",
    "references/monitoring-adapter-contract.md", "references/owner-analytics-adapter-contract.md", "references/measurement-gateway-mcp-decision.md",
    "schemas/diagnosis-report.schema.json", "schemas/client-report.schema.json", "schemas/analysis-report.schema.json", "schemas/impressum-evidence.schema.json", "schemas/impressum-compliance.schema.json",
    "schemas/measurement-enrichment.schema.json", "schemas/measurement-envelope.schema.json", "schemas/core-evidence-binding.schema.json", "schemas/core-execution-bundle.schema.json", "schemas/core-score-admission-report.schema.json",
    "schemas/availability-monitoring.schema.json", "schemas/owner-analytics.schema.json",
    "schemas/visualization-plan.schema.json", "schemas/visual-render-receipt.schema.json",
    "schemas/presentation-render-receipt.schema.json", "schemas/website-audit-packet.schema.json",
    "schemas/batch-context.schema.json", "schemas/batch-row.schema.json",
    "schemas/batch-context.v1.schema.json", "schemas/batch-row.v1.schema.json",
    "schemas/batch-context.v1.1.schema.json", "schemas/batch-row.v1.1.schema.json",
    "schemas/batch-context.v1.2.schema.json", "schemas/batch-row.v1.2.schema.json",
    "schemas/batch-context.v1.3.schema.json", "schemas/batch-row.v1.3.schema.json",
    "templates/chart-library.v1.json", "templates/client-report-template.json",
    "templates/visualization-catalog.v2.json", "templates/presentation.html.j2",
    "templates/diagrams/D01_PROCESS_FLOW.mmd",
    "contracts/pixelkiez_elevenlabs_batch_variable_contract.v1.json",
    "contracts/pixelkiez-elevenlabs-batch-contract-v1.1.json",
    "contracts/pixelkiez-elevenlabs-batch-contract-v1.2.json",
    "contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json", "contracts/contract-manifest.json",
    "scripts/compute_score.py", "scripts/client_story.py", "scripts/strategic_relevance.py", "scripts/customer_story_semantics.py", "scripts/customer_status.py",
    "scripts/measurement_enrichment.py", "scripts/measurement_adapters.py", "scripts/browser_measurements.py",
    "scripts/collect_measurement_enrichment.py", "scripts/validate_measurement_enrichment.py", "scripts/attach_measurement_enrichment.py",
    "scripts/measurement_gateway_client.py", "scripts/normalize_gateway_measurements.py", "scripts/validate_measurement_envelope.py", "scripts/core_active_measurement.py", "scripts/validate_core_evidence_bindings.py", "scripts/validate_core_execution_bundle.py", "scripts/materialize_core_metrics.py", "scripts/validate_core_score_admission.py", "scripts/build_core_execution_matrix.py", "scripts/run_full_48_active_evals.py", "scripts/validate_full_48_active.py",
    "scripts/run_measurement_gateway_evals.py", "scripts/validate_measurement_platform_baseline.py", "scripts/validate_strategic_relevance_v321_preservation.py",
    "scripts/validate_gateway_optional_contracts.py", "scripts/validate_third_party_license_ledger.py",
    "scripts/run_measurement_enrichment_evals.py", "scripts/run_browser_measurement_evals.py",
    "scripts/build_client_report_model.py", "scripts/validate_client_report_model.py", "scripts/validate_visual_story.py",
    "scripts/check_brand_fonts.py", "scripts/business_value.py", "scripts/visual_eligibility.py", "scripts/visual_story_planner.py", "scripts/build_internal_analysis_report.py",
    "scripts/render_internal_analysis_markdown.py", "scripts/validate_internal_analysis_report.py",
    "scripts/build_visualization_plan.py", "scripts/validate_visualization_plan.py",
    "scripts/vega_spec_builder.py", "scripts/svg_chart_renderer.py", "scripts/render_visualizations.py",
    "scripts/validate_visual_assets.py", "scripts/validate_visualization_assets.py",
    "scripts/render_diagnosis_pdf.py", "scripts/render_diagnosis_pdf_reportlab_legacy.py",
    "scripts/validate_pdf_output.py", "scripts/validate_presentation_brand.py", "scripts/validate_pdf_brand.py", "scripts/validate_customer_business_language.py", "scripts/validate_customer_output_guardrails.py", "scripts/validate_analysis_report_completeness.py",
    "scripts/run_business_first_reporting_evals.py", "scripts/run_strategic_relevance_evals.py",
    "scripts/build_audit_deliverables.py", "scripts/finalize_deliverable_manifest.py", "scripts/validate_deliverable_bundle.py",
    "scripts/validate_no_font_binaries.py", "scripts/render_pdf_pages.py",
    "scripts/create_pdf_visual_qa_manifest.py", "scripts/validate_pdf_visual_qa.py",
    "scripts/create_customer_semantic_qa_manifest.py", "scripts/validate_customer_semantic_qa.py", "scripts/validate_customer_presentation_quality.py", "scripts/run_customer_presentation_quality_evals.py",
    "scripts/chart_contract.py", "scripts/validate_chart_payloads.py", "scripts/validate_template_asset.py",
    "scripts/run_chart_template_evals.py", "scripts/run_visual_template_gallery_evals.py",
    "scripts/run_visualization_gallery_evals.py", "scripts/run_visual_architecture_evals.py",
    "scripts/run_visual_reporting_evals.py", "scripts/run_reporting_bundle_evals.py",
    "scripts/run_fixture_eval.py", "scripts/run_client_marketing_evals.py",
    "scripts/run_customer_semantic_evals.py", "scripts/run_score_gate_evals.py",
    "scripts/run_truth_discipline_evals.py", "scripts/run_batch_contract_evals.py",
    "scripts/validate_report_input.py", "scripts/validate_schema.py", "scripts/validate_asset_integrity.py",
    "scripts/impressum_compliance.py", "scripts/legal_customer_projection.py", "scripts/validate_impressum_compliance.py", "scripts/validate_impressum_legal_sources.py", "scripts/attach_impressum_findings.py", "scripts/validate_impressum_projection.py", "scripts/run_impressum_compliance_evals.py", "scripts/run_legal_customer_projection_evals.py",
    "scripts/validate_security_patterns.py", "scripts/validate_source_map.py", "scripts/validate_evals.py",
    "scripts/validate_release_gate.py", "scripts/validate_installability.py", "scripts/validate_agent_agnostic.py",
    "scripts/validate_core_parity.py", "scripts/validate_no_placeholders.py",
    "scripts/batch_contract.py", "scripts/generate_batch_schemas.py", "scripts/build_elevenlabs_batch_csv.py",
    "scripts/validate_batch_context.py", "scripts/validate_batch_contract.py", "scripts/validate_elevenlabs_batch_csv.py",
    "scripts/validate_cross_skill_batch_contract.py", "scripts/run_paired_release.py", "scripts/validate_paired_release.py",
    "scripts/validate_enterprise_skill_evaluation.py", "scripts/pipeline_ledger.py", "scripts/validate_pipeline_ledger.py",
    "evals/trigger_queries.json", "evals/output_evals.json", "evals/fixtures/synthetic-report.json",
    "evals/fixtures/measurement-enrichment-config.json", "evals/fixtures/measurement-provider-responses.json",
    "evals/fixtures/measurement-gateway-config.json", "evals/fixtures/measurement-gateway-envelope.json",
    "evals/fixtures/measurement-gateway-unavailable.json", "evals/fixtures/measurement-gateway-provider-bundle.json", "evals/fixtures/full-48-core-execution.json", "evals/fixtures/full-48-active-golden-score.json",
    "evals/fixtures/browser-consent-accessibility.html",
    "evals/fixtures/low-coverage-marketing-report.json", "evals/fixtures/chart-library-all-templates.json",
    "evals/fixtures/pixelkiez_elevenlabs_batch_template.csv", "evals/fixtures/pixelkiez_elevenlabs_batch_template.xlsx",
    "evals/fixtures/pixelkiez_elevenlabs_batch_example_SIMULATION.csv",
    "evals/fixtures/pixelkiez_elevenlabs_batch_example_v1.1_SIMULATION.csv",
    "evals/fixtures/pixelkiez_elevenlabs_batch_example_v1.2_SIMULATION.csv",
    "evals/fixtures/pixelkiez_elevenlabs_batch_example_v1.3_SIMULATION.csv",
    "reports/research-bag-output.yaml", "reports/architecture-gate.json", "reports/release-gate-report.json", "reports/active-measurement-protected-baseline.json", "reports/impressum-compliance-shared-overrides.json", "reports/impressum-customer-truth-shared-overrides.json", "reports/48-metric-execution-matrix.json", "reports/core-active-eval-results.json", "reports/core-active-mutation-test-report.json", "reports/core-active-determinism-report.json", "reports/score-reconciliation-report.json", "reports/analysis-report-reconciliation.json", "reports/active-core-render-proof.json",
    "reports/installability-report.json", "reports/agent-compatibility-report.json",
    "reports/core-functionality-preservation.json", "reports/enterprise-skill-evaluation.xml",
    "reports/validation-report.json", "reports/eval-results.json", "reports/batch-contract-eval-results.json",
    "reports/cross-skill-compatibility.json", "reports/visual-qa-report.json", "reports/customer-presentation-quality-eval-results.json",
        "reports/customer-presentation-quality-proof.json",
    "reports/visual-reporting-eval-results.json", "reports/visualization-gallery-eval-results.json",
    "reports/measurement-gateway-eval-results.json", "reports/measurement-platform-proof.json", "reports/measurement-platform-protected-baseline.json",
    "reports/strategic-relevance-eval-results.json", "reports/strategic-relevance-proof.json", "reports/strategic-relevance-v321-preservation.json",
    "reports/third-party-license-ledger.json",
]

VEGA_TEMPLATE_NAMES = [
    "V01_OVERALL_SCORE", "V02_CATEGORY_BARS", "V03_TOP_LEVERS", "V04_FINDABILITY_BENCHMARK",
    "V05_RANKING_POSITION", "V06_QUERY_COVERAGE", "V07_PERFORMANCE_THRESHOLD",
    "V08_AI_ANSWERABILITY", "V09_AGENT_READINESS", "V10_TRUST_MATRIX",
    "V11_SEVERITY_DISTRIBUTION", "V12_AUDIT_COVERAGE", "V13_IMPACT_EFFORT", "V14_REPEAT_AUDIT",
]
JSON_REQUIRED = [
    "assets/brand.json", "assets/brand-tokens.json", "assets/fonts/font-manifest.json", "assets/measurement-registry.json", "assets/branch-priority-profiles.v1.json", "schemas/branch-priority.schema.json", "assets/capability-registry.json", "assets/enrichment-metric-registry.json", "assets/impressum-compliance-registry.v1.json",
    "templates/chart-library.v1.json", "templates/client-report-template.json", "templates/visualization-catalog.v2.json",
    "schemas/diagnosis-report.schema.json", "schemas/client-report.schema.json", "schemas/analysis-report.schema.json", "schemas/impressum-evidence.schema.json", "schemas/impressum-compliance.schema.json", "schemas/measurement-enrichment.schema.json",
    "schemas/measurement-envelope.schema.json", "schemas/availability-monitoring.schema.json", "schemas/owner-analytics.schema.json",
    "schemas/visualization-plan.schema.json", "schemas/visual-render-receipt.schema.json",
    "schemas/presentation-render-receipt.schema.json", "schemas/website-audit-packet.schema.json",
    "schemas/batch-context.schema.json", "schemas/batch-row.schema.json",
    "schemas/batch-context.v1.schema.json", "schemas/batch-row.v1.schema.json",
    "schemas/batch-context.v1.1.schema.json", "schemas/batch-row.v1.1.schema.json",
    "schemas/batch-context.v1.2.schema.json", "schemas/batch-row.v1.2.schema.json",
    "schemas/batch-context.v1.3.schema.json", "schemas/batch-row.v1.3.schema.json",
    "contracts/pixelkiez_elevenlabs_batch_variable_contract.v1.json",
    "contracts/pixelkiez-elevenlabs-batch-contract-v1.1.json",
    "contracts/pixelkiez-elevenlabs-batch-contract-v1.2.json",
    "contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json", "contracts/contract-manifest.json",
    "evals/trigger_queries.json", "evals/output_evals.json", "evals/fixtures/impressum-compliance-cases.json",
    "reports/release-gate-report.json", "reports/installability-report.json", "reports/impressum-compliance-eval-results.json", "reports/legal-customer-projection-eval-results.json", "reports/impressum-legal-source-validation.json", "reports/impressum-compliance-shared-overrides.json", "reports/impressum-customer-truth-shared-overrides.json",
    "reports/core-functionality-preservation.json", "reports/validation-report.json", "reports/eval-results.json", "reports/customer-presentation-quality-eval-results.json",
        "reports/customer-presentation-quality-proof.json",
    "reports/visual-reporting-eval-results.json", "reports/visualization-gallery-eval-results.json",
    "reports/measurement-gateway-eval-results.json", "reports/measurement-platform-proof.json", "reports/measurement-platform-protected-baseline.json", "reports/strategic-relevance-eval-results.json", "reports/strategic-relevance-proof.json", "reports/strategic-relevance-v321-preservation.json", "reports/third-party-license-ledger.json",
]


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: quick_validate.py <skill-dir>")
    root = Path(argv[1]).resolve()
    if not root.is_dir():
        return fail(f"not a directory: {root}")
    required = BASE_REQUIRED + [f"templates/visualizations/{name}.vl.json" for name in VEGA_TEMPLATE_NAMES]
    missing = [rel for rel in required if not (root / rel).is_file() or (root / rel).stat().st_size == 0]
    if missing:
        return fail("missing or empty required files: " + ", ".join(missing))
    forbidden = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() and path.name in FORBIDDEN_NAMES]
    if forbidden:
        return fail("PowerPoint-era files must be removed: " + ", ".join(forbidden))

    text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return fail("invalid SKILL.md frontmatter")
    front = text.split("\n---\n", 1)[0].removeprefix("---\n")
    keys = [line.split(":", 1)[0].strip() for line in front.splitlines() if ":" in line]
    if keys != ["name", "description"]:
        return fail("SKILL.md frontmatter must contain only name and description")
    values = dict(line.split(":", 1) for line in front.splitlines() if ":" in line)
    name = values.get("name", "").strip()
    description = values.get("description", "").strip()
    if not NAME_RE.fullmatch(name) or name != root.name:
        return fail("skill name must be valid and match directory")
    if not description or len(description) > 1024 or "<" in description or ">" in description:
        return fail("description missing, too long, or contains angle brackets")
    if len(text.splitlines()) > 500:
        return fail("SKILL.md exceeds 500 lines")
    if "TODO" in text or "[TODO" in text:
        return fail("SKILL.md contains unresolved TODO")

    for rel in JSON_REQUIRED + [f"templates/visualizations/{name}.vl.json" for name in VEGA_TEMPLATE_NAMES]:
        try:
            json.loads((root / rel).read_text(encoding="utf-8"))
        except Exception as exc:
            return fail(f"invalid JSON resource {rel}: {exc}")
    print(f"PASS: {root} ({len(required)} required files, 14 Vega templates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
