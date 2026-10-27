# Pixelkiez Website Diagnosis - Measurement Enrichment & Activating Customer Closing Implementation Plan

## Goal

Extend `pixelkiez-website-diagnosis` so the audit can ingest or collect real, provenance-bearing measurements for query-specific Google visibility, Search Console, GA4, PageSpeed/Lighthouse, CrUX, public-browser accessibility signals and privacy/consent behavior without destabilizing the existing 48-metric score. Replace ambiguous customer status language (`offen`) with an evidence-bound four-state warning system and replace the final negative limits page with a motivating `Priorisieren -> Umsetzen -> Nachmessen` closing plus a clear CTA. Preserve the v1.3 96-field ElevenLabs contract, four-lever customer story, existing score rules, complete internal reports, chart budget, fail-closed truth discipline and brand/PDF QA.

Definition of Done: new enrichment records validate deterministically; live adapters never invent values when auth/key/provider data is unavailable; browser probe works against a controlled fixture; Search Console average position and SERP current rank remain separate; accessibility/privacy claims retain manual/legal boundaries; V10 trust matrix shows `Handlungsbedarf` with strong X/coral semantics for evidenced weak/blocking metrics and grey for not-assessed; client schema/template v8 has no `client_limits` final page and requires an action closing; regression/eval suites pass; proof PDF is rendered and visually inspected; release gate authorizes packaging; final `skill.zip` is generated.

## Requirements

- R1 Preserve the scored 48-metric core and all existing score/coverage semantics.
- R2 Add a separate optional enrichment metric registry/schema with provenance, availability and claim boundaries.
- R3 Add read-only adapters for PSI, CrUX, Search Console, GA4 and DataForSEO; credentials only via environment/runtime config.
- R4 Add deterministic offline/fixture parsing and fail-closed `NOT_CONFIGURED/UNAVAILABLE/ERROR` states.
- R5 Add a public-browser Playwright probe for consent/network/storage/focus/form-name/responsive evidence; optional axe input, never WCAG certification.
- R6 Integrate enrichment into `analysis_report.json/.md` and visualization planning without changing score unless a future versioned scoring migration explicitly does so.
- R7 Add four-state customer semiotics and update V10/fallback renderer.
- R8 Replace final customer limits/open-evidence page with activating closing and CTA; keep qualifications local/internal.
- R9 Add validators/evals for no legal overclaim, no proxy-to-outcome upgrade, no lab/field conflation, no current/average-rank conflation and no customer `client_limits` page.
- R10 Re-render and visually inspect a proof PDF; preserve exact-font strict customer gate.
- R11 Update source map, research bag, architecture/release reports, agent/installability metadata as required.
- R12 Package only after all hard gates pass.

## Non-goals

- No OAuth consent application or credential storage inside the Skill.
- No ranking guarantee, legal compliance determination, WCAG certification, CRM lead qualification or revenue forecast.
- No change to the ElevenLabs v1.3 field count/header.
- No score-weight changes for the new enrichment metrics in this release.
- No private-area/login automation or auth bypass.

## Assumptions / MISSING

- MISSING: customer Google Search Console/GA4 property access tokens and IDs for live validation.
- MISSING: DataForSEO credentials for a live paid SERP call.
- MISSING: exact Schibsted Grotesk runtime font remains external to the package.
- ASSUMPTION: external runners can supply OAuth bearer tokens/API keys as ephemeral environment variables.
- ASSUMPTION: system Chromium or an explicit Chromium path is available when the browser module is invoked; otherwise it fails closed.

## Phases and TDD tasks

### Phase 1 - Contract first
1. Add `assets/enrichment-metric-registry.json` and `schemas/measurement-enrichment.schema.json`.
2. Extend diagnosis/internal analysis schemas with optional enrichment, without changing core metric cardinality/scoring.
3. Add tests that reject measured records without provenance, reject non-null values for unavailable states, and reject secrets in output.

### Phase 2 - Read-only data adapters
4. Implement standard-library HTTP adapters for PSI, CrUX, Search Console Search Analytics + URL Inspection, GA4 `runReport`, and DataForSEO Google Organic Live Advanced.
5. Add provider parsers and fixture/replay mode; write tests before enabling live routing.
6. Enforce runtime-only secrets and host allowlists; emit source-specific claim boundaries.
7. Keep query-specific live SERP position separate from Search Console average position. Show SERP page only if provider returns an explicit page field.

### Phase 3 - Browser measurement
8. Implement Playwright/Chromium public-state probe: baseline/reject/accept isolated contexts, request hosts, cookies/storage, consent controls, accessible-name gaps, keyboard-focus sample and mobile overflow.
9. Add controlled local HTML fixture and deterministic browser eval; axe remains optional runtime input and must not be required for installation.
10. Emit `manual_review_required=true` for accessibility and `legal_review_required=true` for privacy classifications that would exceed technical observation.

### Phase 4 - Canonical analysis integration
11. Copy validated enrichment into internal `analysis_report.json` and render a concise Markdown section.
12. Derive benchmark/ranking visualization inputs only from eligible enrichment records; never synthesize unavailable values.
13. Preserve complete 48/48 metric parity and current score digest semantics.

### Phase 5 - Customer semiotics
14. Add deterministic `customer_status.py`: CLEAR / IMPROVEMENT / ACTION_REQUIRED / NOT_RELIABLY_ASSESSED.
15. Update V10 Trust Matrix planner and Vega-Lite spec to show symbol + status with strong coral X for action required and neutral grey for not assessed.
16. Update safe SVG fallback renderer and validation fixtures.
17. Add negative evals proving `not_assessed` never becomes red/action-required and privacy action-required never becomes `illegal` language.

### Phase 6 - Customer closing v8
18. Upgrade client template/schema/model from v7 to v8: remove `client_limits`, add required `closing` with title, statement, three steps, CTA and optional short data-context note.
19. Replace presentation final page with `Aus Analyse wird Umsetzung` and `Priorisieren -> Umsetzen -> Nachmessen`.
20. Remove limits/open-evidence output from customer model; keep limitations/missing/source-needed internal.
21. Add language validator rules that reject a negative capabilities/limits final page and reject customer legal/certification overclaim language.

### Phase 7 - Regression, PDF QA, release
22. Run schema, security, source-map, truth-discipline, batch-contract, business-first, customer-semantic and new enrichment/semiotics evals.
23. Build a proof bundle from the synthetic fixture, render the PDF, render pages to PNG and visually inspect status matrix + closing page.
24. Validate PDF structure, brand, customer language, semantic QA and visual QA. Exact Schibsted remains a strict customer-mode external gate.
25. Update architecture/research/release/core-preservation/evaluator reports and pipeline ledger.
26. Run package validators and create `dist/skill.zip` only after release gate PASS.

## Validation commands

```bash
python scripts/validate_measurement_enrichment.py evals/fixtures/measurement-enrichment-full.json
python scripts/run_measurement_enrichment_evals.py .
python scripts/run_customer_status_evals.py .
python scripts/run_truth_discipline_evals.py .
python scripts/run_batch_contract_evals.py .
python scripts/run_business_first_reporting_evals.py .
python scripts/quick_validate.py .
python scripts/validate_source_map.py .
python scripts/validate_evals.py .
python scripts/validate_release_gate.py .
python scripts/validate_pipeline_ledger.py .
python scripts/package_skill.py . ./dist
```

## Rollback

- Revert client model/template/schema v8 files to v7 and restore previous V10 planner/spec/renderer.
- Remove optional `measurement_enrichment`; core 48-metric score and v1.3 batch contract remain unchanged throughout, so rollback does not require score migration or CSV migration.
- Keep external adapters isolated; a provider failure can be disabled without affecting base public audit execution.

## Plausibility / truth check

- The plan does not assume live credentials exist.
- Provider data is source-specific and cannot be cross-labeled (`SERP current` != `GSC average`, `Lighthouse lab` != `CrUX field`).
- Automation does not establish legal compliance or full WCAG conformance.
- New data increases decision quality but is not allowed to inflate customer certainty.
- The smallest robust slice is additive: optional enrichment + customer semiotics + closing, not a score rewrite.
