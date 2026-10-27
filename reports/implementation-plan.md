# Pixelkiez Website Diagnosis — Measurement Enrichment and Activating Customer Closing

<!-- GOAL_START -->
Extend `pixelkiez-website-diagnosis` with a non-scoring, provenance-bearing measurement-enrichment layer for query-specific SERP position, Search Console, GA4, PageSpeed/Lighthouse, CrUX and public-browser accessibility/privacy observations. Preserve the existing 48 scored metrics, score semantics, v1.3 96-field ElevenLabs contract, four-lever customer story and fail-closed evidence discipline. Replace ambiguous customer status language with four deterministic states (`Klar`, `Verbesserung sinnvoll`, `Handlungsbedarf`, `Nicht belastbar bewertet`). Evidence-backed privacy/accessibility weaknesses receive a prominent `X Handlungsbedarf`; missing evidence remains neutral. Replace the final limitations page with an action-oriented closing containing up to three measured highlights, four concise actions, a CTA and one next step. Complete deterministic fixture evaluation, regression testing, proof-PDF render/inspection, release-gate validation and packaging.

Definition of Done. The enrichment schema/registry and adapters validate; unavailable credentials/sample/runtime never create invented values; live SERP and Search Console average position remain distinct; lab and field performance remain distinct; GA4 proxy events never become leads/calls; browser accessibility/privacy retain manual/legal boundaries; V10 renders supported action states clearly; client model/template/schema v8 contain no final limitations register; all core regression suites pass; a proof PDF is rendered and visually inspected; release gate authorizes packaging; `dist/skill.zip` is generated.

Explizit out-of-scope.
- OAuth consent application, credential persistence or secret distribution inside the Skill.
- Ranking guarantees, legal compliance determinations, WCAG certification or BFSG/DSGVO verdicts.
- CRM lead qualification, revenue attribution or reconstruction of historical events that were never tracked.
- Changes to the ElevenLabs v1.3 wire contract or to score weights/cardinality in this release.
- Authenticated/private-area browser automation, bypasses or irreversible form submission.
<!-- GOAL_END -->

## Evidence and source boundary

The user-provided Website Intelligence research is authoritative for Pixelkiez product intent, not automatic proof of external API/runtime behavior. External capability claims are bounded by current primary/provider documentation for Search Console, GA4 Data API, PageSpeed Insights, CrUX, W3C WCAG-EM and DataForSEO. Existing skill code, schemas and regression fixtures are primary implementation evidence. No live customer Google/DataForSEO credentials are available in this build, so provider execution is validated through deterministic fixture replay plus contract-level parsers; live browser navigation is separately runtime-gated.

## Assumptions, missing information, open questions, blockers

- `MISSING`: live customer Search Console and GA4 property authorization/IDs.
- `MISSING`: live DataForSEO credentials.
- `MISSING`: exact Schibsted Grotesk runtime font; strict customer-PDF release remains externally gated.
- `BLOCKER_FOR_BROWSER_LIVE_PROOF`: current execution environment blocks Chromium navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`; implementation remains installable/fail-closed but live browser runtime is not declared verified here.
- `ASSUMPTION`: production runners inject authorized API keys/OAuth bearer tokens only at runtime.
- `ASSUMPTION`: an eligible production browser runtime permits public navigation when browser measurement is enabled.

## Requirements

- R1 Preserve all 48 canonical scored metrics and current score/coverage semantics.
- R2 Add an optional non-scoring enrichment registry/schema with provenance, availability and claim boundaries.
- R3 Add read-only PSI, CrUX, GSC, GA4 and replaceable SERP adapters with runtime-only credentials.
- R4 Add deterministic provider-fixture replay and fail-closed unavailable/error states.
- R5 Add public-only Chromium/Playwright observation for consent/network/storage/focus/accessibility/mobile signals.
- R6 Integrate enrichment into internal JSON/Markdown and eligible customer visuals without score changes.
- R7 Add four-state customer warning semiotics; unassessed states never become red.
- R8 Upgrade client template/model/schema to v8 closing; remove final customer limitations register.
- R9 Add truth/security/customer-language validators and regression evals.
- R10 Render and visually inspect a proof PDF while retaining the exact-font customer gate.
- R11 Update source map, architecture/release evidence, evaluator and pipeline ledger.
- R12 Package only after hard release gates pass.

## Architecture and file boundaries

- Core score truth remains `assets/measurement-registry.json` + diagnosis/scoring pipeline.
- New enrichment truth lives in `assets/enrichment-metric-registry.json`, `schemas/measurement-enrichment.schema.json` and `scripts/measurement_*`/browser adapter modules.
- External secrets are environment/runtime inputs and never report/package content.
- `measurement_enrichment` is an optional canonical-report attachment copied into internal reports.
- Customer status projection lives in `scripts/customer_status.py`; visual routing remains in `build_visualization_plan.py` and renderer/template files.
- Customer closing lives only in client-model/schema/template/PDF presentation layers.
- ElevenLabs batch files/contracts remain untouched except regression verification.

## Implementation phases

1. Contract and source boundary.
2. Read-only measurement adapters and deterministic replay.
3. Public browser measurement and runtime gate.
4. Canonical/internal-report integration.
5. Customer warning semiotics and visual rendering.
6. Client closing v8.
7. Regression, PDF QA, release evidence and packaging.

## Tasks

### TASK-001: Freeze score and batch regression boundaries
Confirm the 48-metric score core and all v1/v1.1/v1.2/v1.3 batch contracts before/after the patch. Acceptance: metric cardinality and v1.3 96-field digest remain unchanged.

### TASK-002: Add enrichment contract and registry
Create enrichment registry/schema with source, provider, observation time, context, value/unit, evidence reference and claim-boundary fields. Acceptance: measured records require provenance; unavailable records cannot carry fabricated measurements.

### TASK-003: Implement read-only API/provider adapters
Implement PageSpeed, CrUX, GSC Search Analytics/URL Inspection, GA4 runReport and DataForSEO SERP adapters behind allowlisted hosts. Acceptance: secrets remain runtime-only; SERP page is emitted only from explicit provider data.

### TASK-004: Implement deterministic enrichment collection/evals
Add fixture replay, collection CLI, validator and attach helper. Acceptance: live SERP vs GSC average, lab vs field data and GA4 proxy boundaries are regression-tested.

### TASK-005: Implement public browser measurement
Implement isolated baseline/reject/accept contexts, network/cookie/storage observation, visible consent controls, focus/accessibility samples and mobile overflow; axe is optional runtime input. Acceptance: private/authenticated access and irreversible form submission are excluded; runtime blocking is surfaced explicitly.

### TASK-006: Integrate enrichment into canonical/internal reports
Attach optional enrichment to diagnosis truth and copy it into analysis JSON/Markdown. Acceptance: 48/48 core metric parity and score remain unchanged.

### TASK-007: Implement four-state warning semiotics
Add deterministic customer status mapping and update V10 planner/spec/SVG fallback. Acceptance: supported weak/blocking privacy findings render `X Handlungsbedarf`; `not_assessed` renders neutral.

### TASK-008: Add evidence-bound Google visibility visual
Permit V05 only from query-bound measured SERP evidence or legacy fully contextual ranking evidence. Acceptance: query, position, location, device and observed time validate; no global rank is invented.

### TASK-009: Replace final limitations page with closing v8
Upgrade client schema/template/model and presentation HTML/CSS. Acceptance: final page contains actions/CTA/next step and optional measured highlights; no customer `client_limits` closing exists.

### TASK-010: Extend customer-language and truth validators
Reject legal/certification overclaims, proxy-to-outcome upgrades, current/average-rank conflation and negative limitations-page regressions. Acceptance: dedicated negative fixtures fail closed.

### TASK-011: Run regression and PDF proof QA
Run schema, score, truth, batch, business-first, enrichment, security and source-map evals; build proof PDF, render pages and visually inspect V10 plus final closing. Acceptance: no clipping/overlap; customer semantics match canonical evidence.

### TASK-012: Freeze release evidence and package
Update source map, architecture/release/core-preservation/evaluator reports and pipeline ledger; calculate final digest and package. Acceptance: release gate allows packaging and installable `dist/skill.zip` exists.

## Validation strategy

Run deterministic unit/contract and negative tests first, then core regressions, then proof rendering. Required checks include schema validation, enrichment evals, score gate, truth discipline, all batch-contract versions, business-first reporting, customer-language/visual validators, security/source map, PDF structure/brand, page-by-page visual QA and semantic QA. Browser live navigation is recorded separately as PASS or explicit runtime blocker; it is never silently simulated as live execution.

## Rollback and safety

Enrichment is optional and non-scoring, so it can be disabled without score or CSV migration. Rollback customer v8 by restoring client schema/template/model/presentation and prior V10 projection while retaining canonical core data. Disable individual external adapters independently on provider failure. Never bundle credentials or fonts. Never downgrade `UNAVAILABLE`, manual/legal review flags or runtime blockers to successful measurements.

## Execution handoff

Execute TASK-001 through TASK-012 in order on the working skill snapshot. Use deterministic fixture replay for unavailable external credentials. Preserve exact source/provider provenance in reports. Before packaging, record unresolved runtime/font limits in release evidence. Deliver only the package whose digest matches release gate and pipeline ledger.

## Plausibility and truth self-check

- Strongest counterargument: adding many data sources can make the report look more authoritative than the data permits. Mitigation: non-scoring enrichment, explicit provenance, context requirements and fail-closed source states.
- Credential asymmetry must not change the Pixelkiez score for the same public site in this release.
- A paid SERP snapshot is not a stable Google guarantee; Search Console average position is not a live rank.
- Lighthouse/PageSpeed lab evidence is not CrUX/RUM field evidence.
- Automated/browser accessibility evidence is not complete WCAG conformance; technical privacy evidence is not a legal verdict.
- The closing is action-oriented without hiding material context; limitations move next to relevant measurements/internal evidence rather than becoming the sales conclusion.
- Smallest robust slice: additive enrichment + warning semiotics + closing v8, with no score rewrite or contract migration.
