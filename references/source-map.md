# Source Map

This map records the material used to update the Pixelkiez Website Diagnosis skill. It is not proof that dynamic external platforms or standards behave the same way at audit runtime.

```yaml
sources:
  - source_id: S001
    title: Existing pixelkiez-website-diagnosis skill package
    type: user_provided
    location: conversation artifact from the preceding Pixelkiez skill build
    purpose: baseline functionality to preserve while replacing the PowerPoint branch
    reliability: strong for the existing package behavior and user-approved workflow
    limitations: previous package decisions are not external facts and may be intentionally superseded by the current request
    confidence_default: 4

  - source_id: S002
    title: Website Intelligence Auditor integration analysis
    type: user_provided
    location: uploaded markdown(3).md
    purpose: requested integration scope, gap analysis, measurement taxonomy, scoring cautions, and target architecture
    reliability: strong as the user's requested design basis; external claims inside it still require primary verification when operationalized
    limitations: contains recommendations and derived architecture decisions, not a measurement engine or external standard
    confidence_default: 4

  - source_id: S003
    title: Website Intelligence Auditor skill and references
    type: secondary
    location: installed skill resources inspected during this build
    purpose: measurement classes, minimum public audit set, performance hierarchy, search/IA/content/AI method, parallel-audit reconciliation, and PDF report structure
    reliability: strong as an internal reusable method reference
    limitations: declares audit checks but does not itself provide every crawler, Lighthouse, Search Console, Analytics, backlink, accessibility, or security measurement capability
    confidence_default: 4

  - source_id: S004
    title: Pixelkiez Design System
    type: user_provided
    location: supplied Pixelkiez Design System archives and Pixelkiez Design System#final.pdf
    purpose: authoritative project brand direction for colors, typography intent, spacing, report rhythm, cards, pixel-meter device, and client-report structure
    reliability: strong for this project because the user explicitly supplied it as the required brand system
    limitations: font binaries are not bundled; public brand state outside the supplied package is not independently verified here; an earlier supplied report page rejected any overall score, but that product rule is explicitly superseded by the current user request and replaced with a proprietary coverage-gated score policy
    confidence_default: 4

  - source_id: S005
    title: Pixelkiez product score policy created in this build
    type: derived
    location: assets/measurement-registry.json and references/scoring-policy.md
    purpose: deterministic metric aggregation, score coverage gates, category weights, score display, and confidence rules
    reliability: reproducible as a product policy once validated by scripts
    limitations: category weights, metric weights, 0/25/50/75/100 anchors, and 50/80 percent display gates are product decisions, not universal website-quality standards
    confidence_default: 4

  - source_id: S006
    title: Client PDF template contract created in this build
    type: derived
    location: schemas/client-report.schema.json and references/pdf-report-contract.md
    purpose: enforce semantic placement, text budgets, strengths/weaknesses balance, score presentation, appendix traceability, and repeated Pixelkiez visual structure
    reliability: deterministic within this package when validators and renderer pass
    limitations: aesthetic quality still requires rendered-page inspection; schema validity alone does not prove visual quality
    confidence_default: 4

  - source_id: S007
    title: Runtime standards and platform documentation
    type: uncertain
    location: current official documentation selected per audit run
    purpose: support dynamic thresholds or product-behavior claims when a metric depends on them
    reliability: SOURCE_NEEDED at runtime until the relevant current primary source is inspected
    limitations: documentation, thresholds, product behavior, laws, and supported structured-data features can change
    confidence_default: 2

  - source_id: S008
    title: Client-specific measurements and observations
    type: derived
    location: per-audit evidence ledger and diagnosis-report.json
    purpose: support client findings and score inputs
    reliability: depends on tool, method, sampling, timestamp, and reproducibility
    limitations: public-surface evidence does not reveal private analytics, repository state, backend behavior, legal compliance, or actual business outcomes unless separately supplied and verified
    confidence_default: 4

  - source_id: S009
    title: PXK Website Diagnosis batch CSV Jira task specification
    type: user_provided
    location: uploaded PXK-website-diagnosis-batch-csv-ticket(1).md
    purpose: binding requested scope, acceptance criteria, authority mapping, 82-field export rules and Definition of Done for this update
    reliability: strong as the user's implementation contract
    limitations: does not itself prove external ElevenLabs, legal or sibling-skill runtime behavior
    confidence_default: 5

  - source_id: S010
    title: Website Diagnosis baseline ZIP for this update
    type: user_provided
    location: uploaded pixelkiez-website-diagnosis(1).zip; SHA-256 7353aa2c2b1be38036d498c8bf0b1fa5b48dd06dd32d59ab8561afe4cf076f39
    purpose: exact baseline functionality and files to preserve while adding the batch export
    reliability: direct baseline artifact inspected locally
    limitations: package behavior still requires deterministic validation; it is not external product truth
    confidence_default: 5

  - source_id: S011
    title: Pixelkiez ElevenLabs v1 CSV template
    type: user_provided
    location: uploaded pixelkiez_elevenlabs_batch_template(2).csv; SHA-256 0893091231a4fb1166d07ad1ea86548839da4172636c31b4f918c733343826d8
    purpose: golden CSV header fixture
    reliability: direct user-provided contract fixture
    limitations: template data does not authorize a real campaign or live call
    confidence_default: 5

  - source_id: S012
    title: Pixelkiez ElevenLabs v1 XLSX template and variable dictionary
    type: user_provided
    location: project-provided pixelkiez_elevenlabs_batch_template(1).xlsx
    purpose: golden Batch_Template, Variable_Dictionary, Upload_Notes and Optional_Overrides
    reliability: direct project artifact; locally verified as 82 fields with 38 YES, 1 YES*, 21 RECOMMENDED and 22 OPTIONAL
    limitations: project contract, not proof of current third-party platform behavior
    confidence_default: 5

  - source_id: S013
    title: Canonical Pixelkiez ElevenLabs v1 variable contract
    type: user_provided
    location: project-provided pixelkiez_elevenlabs_batch_variable_contract(1).json; bundled byte-for-byte as contracts/pixelkiez_elevenlabs_batch_variable_contract.v1.json
    purpose: single machine-readable field list, order, Requiredness, types, source ownership, descriptions and excluded overrides
    reliability: direct project contract pinned by SHA-256
    limitations: changing the contract requires coordinated versioning across both Pixelkiez skills
    confidence_default: 5

  - source_id: S014
    title: Pixelkiez batch simulation fixture
    type: user_provided
    location: project/file-library simulation plus equivalent XLSX Batch_Template example row, bundled as evals/fixtures/pixelkiez_elevenlabs_batch_example_SIMULATION.csv
    purpose: deterministic simulation validation and cell-by-cell golden parity
    reliability: strong as a synthetic fixture
    limitations: SIMULATION and LEGAL_REVIEW_REQUIRED semantics explicitly do not authorize live use
    confidence_default: 5

  - source_id: S015
    title: Baseline Pixelkiez Adaptive ElevenLabs Appointment Agent Architect before the paired v1.1 patch
    type: primary
    location: skills://pixelkiez-adaptive-elevenlabs-appointment-agent-architect/skill.md inspected 2026-08-27
    purpose: establish the pre-patch sibling boundary and preserve historical comparison context
    reliability: direct installed skill entrypoint for the inspected baseline environment
    limitations: historical baseline only; the paired local v1.1 build is represented separately by S018 and current deterministic E2E evidence
    confidence_default: 5

  - source_id: S016
    title: PXK Web Audit Diagram Template
    type: user_provided
    location: assets/PXK_web_audit_template.pdf
    purpose: normative V01-V12 chart selection, data contracts, five-zone anatomy, evidence/population disclosure and visual language
    reliability: authoritative as the user's project presentation contract
    limitations: does not establish external statistical thresholds; M001-M138 identifiers do not match the current installed registry and no crosswalk may be invented
    use_in_skill: chart-template contract, machine-readable chart library, renderer and visual-QA gates
    confidence_default: 5 for project presentation rules; external claims inside a concrete audit still require their own evidence
```

## Hard source rules

- User-provided material remains `user_provided`; it is not silently promoted to external truth.
- Dynamic external claims require a current primary source or remain `SOURCE_NEEDED`.
- Missing required evidence is `MISSING` or `not_assessed`, not zero quality.
- A model-derived summary is `derived` and must point back to the underlying evidence.
- The Pixelkiez score is explicitly a product-defined reference score, not an external standard.

## S017 - v1.1 dual-skill patch requirements
- type: `user_provided`
- location: project conversation 2026-08-27; paired Website Diagnosis and Voice Architect patch tickets
- purpose: requires voice-ready audit hooks, additive optional customer_email, legacy v1 preservation, shared v1.1 digest, and cross-skill E2E
- reliability: authoritative for internal requested behavior
- limitations: does not prove ElevenLabs live runtime, email delivery, or legal campaign approval
- use_in_skill: Producer contract v1.1, evals, migration and cross-skill checks
- confidence_default: 5 for internal requirements; 2 for external runtime effects

## S018 - Shared v1.1 contract artifact
- type: `user_provided`
- location: `contracts/pixelkiez-elevenlabs-batch-contract-v1.1.json`, byte-identical in both dual-patch skills
- purpose: canonical additive 83-field Producer/Consumer contract
- reliability: deterministic internal artifact
- limitations: structural compatibility only; not provider/runtime proof
- use_in_skill: builder, schemas, validators, traceability and cross-skill E2E
- confidence_default: 5 for bytes/local semantics

## S019 - Active v1.1 Website Diagnosis baseline inspected for this update
- type: `primary`
- location: installed `pixelkiez-website-diagnosis` skill snapshot inspected 2026-08-28; SKILL.md SHA-256 `338be346f6a8ebc9ae0ac1675d10cbe770bf0cd7a1331c32aa17934fac9ef383`
- purpose: preserve the actual current 83-field v1.1/legacy-v1 functionality while changing the customer presentation layer
- reliability: direct inspected baseline artifact for this build
- limitations: proves package contents, not live external website or provider behavior
- use_in_skill: implementation baseline, regression boundary and core-parity gate
- confidence_default: 5

## S020 - Failed customer PDF showing the presentation regression
- type: `user_provided`
- location: uploaded `pixelkiez-website-analysis (3).pdf`; SHA-256 `e017a44356b5eb01f9e8d55ff32a472a88df01c353dbcd2f4a7928a54a9b3074`
- purpose: reproduce the concrete failure mode: no chart pages after coverage plus multiple pages of unused technical metrics/source material
- reliability: direct evidence of the rendered artifact behavior
- limitations: it is not independent proof that every underlying website finding is true
- use_in_skill: customer-story requirements and low-coverage regression design
- confidence_default: 5 for rendered-output behavior; 2 for external website truth not separately verified here

## S021 - Deep Reasoning root-cause analysis
- type: `derived`
- location: `/mnt/data/analysis_report.md` and `/mnt/data/analysis_report.json` from the preceding analysis turn
- purpose: identify the pass-through visualization bug, empty-array schema gap, all-metrics appendix projection, renderer behavior and low-coverage blind spot
- reliability: derived from inspected skill code plus the failed PDF; implementation claims are rechecked against the current baseline during this build
- limitations: derived analysis is not used as external platform truth
- use_in_skill: architecture rationale and regression cases
- confidence_default: 4

## S022 - Customer-output correction request
- type: `user_provided`
- location: project conversation 2026-08-27 to 2026-08-28
- purpose: normative project requirement that the default PDF be short, plain-language, chart-driven and limited to the strongest weaknesses, solutions and useful metrics
- reliability: authoritative for Pixelkiez product/presentation requirements
- limitations: does not authorize invented business uplift, rankings, revenue or conversion claims
- use_in_skill: client-story contract, PDF page budget, visual-story gate and eval acceptance criteria
- confidence_default: 5 for internal product requirements


## S023 - ElevenLabs batch upload error from current configured Pixelkiez agent

- class: user_provided
- observed: 2026-08-28
- content: upload rejected because these exact variables were missing: company_name, company_website, prospect_name, prospect_salutation, call_compliance_status, call_compliance_note, lead_source, consultant_name, meeting_description, offer_process, website_analysis_report, agency_name, verified_finding
- confidence: 5 for the current agent binding; not a universal ElevenLabs variable list
- use: v1.2 additive provider-binding contract and regression eval

## S024 - ElevenLabs Batch Calling and Dynamic Variables documentation

- class: primary_external
- verified: 2026-08-28
- purpose: confirms `phone_number` batch transport and that recipient-list columns are passed as exact case-sensitive Dynamic Variables; supports provider-binding mechanics, not Pixelkiez field semantics

## S025 - v1.3 five-class batch-readiness requirement
- type: `user_provided`
- location: project conversation 2026-08-29
- purpose: retain all 96 existing CSV fields while classifying each exactly once as `INTERNAL_RECORD`, `EL_RUNTIME_REQUIRED`, `EL_RUNTIME_DEFAULTED`, `OPTIONAL`, or `PRODUCTION_GATE_ONLY`; specifically prevent missing email or unknown prospect identity from blocking an otherwise valid ElevenLabs upload
- reliability: authoritative for the requested Pixelkiez internal contract behavior
- limitations: does not prove ElevenLabs provider acceptance, legal eligibility, or downstream Voice Architect v1.3 adoption
- use_in_skill: v1.3 contract metadata, builder defaults, upload-readiness validator, production prerequisite gate, regression evals
- confidence_default: 5

## S026 - Active Website Diagnosis v1.2 baseline for v1.3 update
- type: `primary`
- location: installed `pixelkiez-website-diagnosis` package inspected 2026-08-29
- purpose: preserve the current 96-column v1.2 wire header, 13 observed-agent compatibility variables, PDF/JSON/scoring behavior, and explicit v1/v1.1 compatibility while changing readiness semantics
- reliability: direct inspected package baseline
- limitations: package contents are internal implementation evidence, not proof of live provider behavior
- use_in_skill: migration boundary, header parity, core-functionality preservation, rollback
- confidence_default: 5

## S030 - Vega-Lite repository snapshot and schema
- type: `primary`
- location: `vega/vega-lite` commit `91eeeb8c2b8a4cf2cf9c1ea238667da0216d7a1c`; uploaded `vega-lite-main.zip` SHA-256 `a563cf6cc2b1328620dc05d74fbb90599610486d18037add0d315d142bc56a7e`
- purpose: declarative visualization grammar, JSON-schema validation, static SVG/PDF-oriented CLI architecture and example-pattern research
- reliability: exact repository snapshot inspected locally and checked against current GitHub primary files
- limitations: source inspection does not prove the Pixelkiez runtime executes Vega; each render receipt records actual backend
- use_in_skill: `assets/vega-lite-schema-v6.4.3.json`, curated `.vl.json` templates, spec builder and validators
- confidence_default: 5 for inspected source/schema; 2 for unavailable external runtime behavior

## S031 - WeasyPrint repository and local runtime
- type: `primary`
- location: `Kozea/WeasyPrint` upstream commit `59283182f277c8fbda95e9ff910180b30a32c60d`; local runtime version recorded by each presentation receipt
- purpose: HTML/CSS paged-media, `@font-face`, SVG embedding and PDF rendering architecture
- reliability: upstream source/docs inspected and local WeasyPrint runtime executed in deterministic fixture tests
- limitations: local fixture success does not prove every target host has the same fonts/system libraries
- use_in_skill: default customer PDF renderer, HTML/CSS template and brand receipt
- confidence_default: 5 for local executed renderer behavior; 4 for upstream architecture

## S032 - Mermaid CLI repository
- type: `primary`
- location: `mermaid-js/mermaid-cli` commit `6731b15f16819fa8470e4d8403d6c4264d4f0849`, package version `11.16.0`
- purpose: optional process/structure diagram backend and SVG output pattern
- reliability: exact source tree, README, package and CI inspected
- limitations: `mmdc`/Chromium is not installed in the current runtime; no Mermaid CLI runtime PASS is claimed
- use_in_skill: optional `D01_PROCESS_FLOW` renderer with deterministic safe SVG fallback
- confidence_default: 5 for source-inspected capability; 2 for unexecuted local backend

## S033 - fl_chart and Charts/DGCharts comparison snapshots
- type: `primary`
- location: `imaNNeo/fl_chart` commit `f3a575827312b8f12628b66d12d08066eb4d2570`, ZIP SHA-256 `3bc103e99d6b0a511a60be29e0975ba99ecacaf0c7452a805054a45cceb9d01d`; `ChartsOrg/Charts` commit `1bad5469f57628782110b05996d4fa00473abf06`, ZIP SHA-256 `3d83481a4ef1e61edb3e80b50cad2996f69877a74667a1b6441661fa942add5a`
- purpose: compare native mobile chart patterns, output boundaries and runtime costs
- reliability: exact source snapshots and current primary repository files inspected
- limitations: repositories were not fully built locally; no performance comparison is claimed
- use_in_skill: rejection rationale and generic visual-pattern inspiration only; no code copied
- confidence_default: 5 for source architecture; 2 for runtime/performance claims

## S034 - Pixelkiez visualization/reporting correction requirement
- type: `user_provided`
- location: project conversation 2026-08-29
- purpose: require customer-presentable typography, extensive evidence-bound charts, four visual levers, complete internal JSON and Markdown metric reports, brand consistency and inspect/adapt validation
- reliability: authoritative product/output requirement
- limitations: does not supply benchmark/SERP data or reusable exact brand-font binaries
- use_in_skill: three-output contract, visualization planner, brand/font release gates, internal report completeness and E2E tests
- confidence_default: 5 for internal requirements; external benchmark claims remain SOURCE_NEEDED

## S-BUSINESS-FIRST-2026-08-29 - Pixelkiez Business-First Website Intelligence implementation plan
- type: `user_provided`
- location: `docs/plans/2026-08-29-pixelkiez-business-first-website-intelligence-reporting.md`
- purpose: normative project requirement for internal-vs-customer separation, business interpretation, customer language firewall, visual routing, benchmark/ranking gates, brand rendering and final QA.
- reliability: strong as the current user-approved product requirement.
- limitations: does not independently verify external benchmark providers, live ranking data or font licensing/runtime availability.
- use_in_skill: customer business projection, analysis-report completeness, visualization routing and negative release tests.
- confidence_default: 5 for internal product requirements; 2 for any external capability implied but not independently verified.

## S035 - Website Intelligence research for measured open points
- type: `user_provided`
- location: user-provided research, "Pixelkiez Website Intelligence – Forschungsplan für echte Messwerte statt offene Punkte", 2026-08-30
- purpose: product requirement and researched candidate architecture for SERP, Search Console, GA4, CrUX, PageSpeed, browser accessibility/privacy and action-oriented customer closing
- reliability: authoritative for requested Pixelkiez product direction; external capability claims are independently bounded by primary documentation below
- limitations: does not itself prove provider credentials, live customer data, browser runtime permission or legal/conformance outcomes
- use_in_skill: measurement-enrichment architecture, customer warning semantics, closing-page redesign and eval requirements
- confidence_default: 5 for internal requirements; external runtime claims require primary evidence

## S036 - Google Search Console Search Analytics API
- type: `primary`
- location: https://developers.google.com/webmaster-tools/v1/searchanalytics/query (verified 2026-08-30)
- purpose: authorized query/page/device/country search-performance data including clicks, impressions, CTR and average position
- reliability: current Google developer documentation
- limitations: average position is not a live SERP rank; Search Console documents internal limits and does not guarantee every data row
- use_in_skill: GSC adapter and truth boundary separating historical average position from live SERP measurement
- confidence_default: 5

## S037 - Google PageSpeed Insights API
- type: `primary`
- location: https://developers.google.com/speed/docs/insights/v5/reference/pagespeedapi/runpagespeed (verified 2026-08-30)
- purpose: programmatic page analysis with mobile/desktop strategy and Lighthouse categories
- reliability: Google developer documentation
- limitations: laboratory analysis must not be described as real-user field performance
- use_in_skill: PageSpeed adapter and lab-performance enrichment
- confidence_default: 5

## S038 - Chrome UX Report API
- type: `primary`
- location: https://developer.chrome.com/docs/crux/api/ (verified 2026-08-30)
- purpose: URL/origin real-user Chrome experience records by form factor including Web Vitals distributions/percentiles when available
- reliability: Chrome for Developers documentation
- limitations: not every target has sufficient CrUX data; missing records are not quality failures
- use_in_skill: CrUX field-performance enrichment and sparse-data fallback state
- confidence_default: 5

## S039 - Google Analytics Data API
- type: `primary`
- location: https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport (verified 2026-08-30)
- purpose: authorized reporting of collected GA4 dimensions and metrics including active users and event counts
- reliability: current Google developer documentation
- limitations: only tracked events can be reported; click/event proxies do not prove qualified leads or won customers
- use_in_skill: GA4 adapter, event semantic boundaries and customer measurement highlights
- confidence_default: 5

## S040 - DataForSEO Google organic SERP Live Advanced
- type: `primary`
- location: https://docs.dataforseo.com/v3/serp-se-type-live-advanced/ (verified 2026-08-30)
- purpose: candidate replaceable SERP provider with query-specific current result rank fields including `rank_group`, `rank_absolute` and explicit `page`
- reliability: provider documentation for its own API contract
- limitations: paid third-party provider; provider result is a dated query/location/device snapshot and not a stable Google guarantee
- use_in_skill: first SERP adapter behind provider-neutral enrichment contract
- confidence_default: 5 for documented fields; 3 for future provider continuity

## S041 - W3C WCAG-EM 2
- type: `primary`
- location: https://www.w3.org/TR/wcag-em-2/ (published 2026-07-23; verified 2026-08-30)
- purpose: authoritative evaluation-method boundary for structured WCAG conformance evaluation
- reliability: W3C Group Note
- limitations: does not make browser automation a complete conformance certification
- use_in_skill: accessibility claim boundary and manual-review requirement
- confidence_default: 5


## S042 - Pixelkiez Measurement Platform Integration plan
- type: `user_provided`
- location: `docs/plans/2026-08-30-pixelkiez-measurement-platform-integration.md`
- purpose: approved additive architecture for a separate read-only measurement gateway, provider-neutral envelope, SSRF/egress controls, normalization into existing non-scoring enrichment and protected regressions
- reliability: authoritative internal product/implementation requirement
- limitations: does not itself prove third-party runtime behavior, licensing compatibility for source reuse, or live network availability
- use_in_skill: gateway contract, optional adapter boundary, tests and release gates
- confidence_default: 5 for internal requirements

## S043 - User-provided Open Web Analytics snapshot
- type: `user_provided`
- location: `Open-Web-Analytics-master.zip` (digest recorded in `reports/third-party-license-ledger.json`)
- purpose: first-party analytics capability reference
- reliability: exact supplied snapshot inspected for scope/license statement
- limitations: not executed; no code reused; current upstream/runtime behavior not inferred from snapshot
- use_in_skill: future owner-analytics provider concept only
- confidence_default: 4 for snapshot contents, 1 for unexecuted runtime behavior

## S044 - User-provided Statping snapshot
- type: `user_provided`
- location: `statping-dev.zip` (digest recorded in `reports/third-party-license-ledger.json`)
- purpose: continuous-monitoring capability reference
- reliability: exact supplied snapshot inspected for license and architecture cues
- limitations: not executed; no code reused
- use_in_skill: provider-neutral monitoring contract only
- confidence_default: 4 for snapshot contents, 1 for runtime behavior

## S045 - User-provided CSP Auditor snapshot
- type: `user_provided`
- location: `csp-auditor-master.zip` (digest recorded in `reports/third-party-license-ledger.json`)
- purpose: CSP analysis concept reference
- reliability: exact supplied snapshot inspected
- limitations: root license was not established from the inspected snapshot; source reuse therefore blocked
- use_in_skill: independently implemented narrow CSP heuristics only
- confidence_default: 4 for observed concepts, 1 for license/runtime claims

## S046 - User-provided Web-Check snapshot
- type: `user_provided`
- location: `web-check-master.zip` (digest recorded in `reports/third-party-license-ledger.json`)
- purpose: public web-probe concept reference
- reliability: exact supplied snapshot inspected; MIT license observed in snapshot
- limitations: no source code reused and application runtime not executed
- use_in_skill: independently implemented bounded public-probe concepts
- confidence_default: 4 for inspected snapshot

## Customer-presentation quality patch evidence

- `SESSION-RISTORANTE-BRESCIA-FIRST-PASS` / `SESSION-RISTORANTE-BRESCIA-SECOND-PASS`
  - class: session_observation
  - authority: supports workflow/quality failure and repair-pattern claims only; not external website truth
  - use: motivates non-compensatory final QA, cover-integrity checks, score-policy reconciliation, sentence-integrity guard and synthetic-priority removal
  - limitation: one contrastive customer-report episode demonstrates a strong process failure mode but does not by itself prove universal causal impact

- `references/customer-presentation-quality-contract.md`
  - class: first_party_product_policy
  - authority: normative Pixelkiez release rule for customer-presentation completion
  - use: defines hard-gate quality vector and resolved customer score projection

## S047 - Frozen installed Pixelkiez Website Diagnosis baseline for Active Core Migration
- type: `primary`
- location: installed `/home/oai/skills/pixelkiez-website-diagnosis`, copied read-only into the isolated migration worktree; initial tree digest `dbe282325a1ebd1acaaa0b02c822037a235e573e548e39b0a36ae96ad60569f2`
- purpose: executable source of truth for the 48-metric registry, capabilities, scoring engine, schemas, gateway/enrichment behavior, reporting and release gates before this migration
- reliability: direct locally inspected and executable baseline; deterministic baseline gates passed except the full reporting-runtime rerun, which timed out and remains explicitly unverified
- limitations: installed package is not a Git repository, so no branch/HEAD provenance exists; passing fixture/tests does not prove live external measurement availability
- use_in_skill: active-migration baseline, protected hashes, regression comparison and rollback boundary
- confidence_default: 5 for inspected local files and completed local tests; 2 for unrerun external/runtime behavior

## S048 - Active Measurement / Scoring Migration instruction
- type: `user_provided`
- location: project conversation 2026-09-07
- purpose: normative migration requirements: exact 48 metrics, evidence binding, execution states, score admission, registry-weight preservation, reporting reconciliation, mutations, determinism and fail-closed release semantics
- reliability: authoritative for requested project behavior and Definition of Done
- limitations: does not independently prove that a specific external measurement or qualitative classification is factually correct; source/policy gaps still block runtime claims
- use_in_skill: `references/core-active-measurement-migration.md`, active binding/admission contracts, eval IDs and release criteria
- confidence_default: 5 for requested product/process requirements

## S049 - Prior Core Evidence Binding & Shadow Resolver plan
- type: `user_provided`
- location: uploaded `2026-09-07-pixelkiez-core-evidence-binding-assessability-shadow-resolver (3).md`
- purpose: historical score-neutral design and migration predecessor; establishes that FIND-02/TRUST-03 Shadow work did not authorize active score mutation
- reliability: strong as historical project decision context
- limitations: intentionally stops before active scoring and therefore cannot authorize the new active migration by itself
- use_in_skill: ADR/history boundary only; not treated as active-score product policy
- confidence_default: 5 for historical intent, 2 for external technical claims not independently reverified in this migration

## S050 - Prior Core Evidence architecture analysis report
- type: `derived`
- location: uploaded `analysis_report(20260907-194015).json`
- purpose: prior architecture analysis, source inventory and explicit record of missing active-scoring policy at the Shadow stage
- reliability: useful derived context because it points to the installed registry/scorer/gateway contracts and marks active mapping gaps
- limitations: generated analysis is not an executable source of truth; its external-source assertions are not silently promoted here
- use_in_skill: migration rationale and counterargument; executable current files override it on conflict
- confidence_default: 3

## S-IMP-RESEARCH — Impressum compliance research bag
- type: `user_provided`
- location: `pxk-web-skill-master/deep-research-report (5).md`
- purpose: Taxonomy, ILES hypothesis, defect and risk-model context for the Impressum patch.
- reliability: Useful internal research context; not legal authority.
- limitations: Must not enable hard legal rules without separate current primary-source verification.
- use_in_skill: `references/impressum-compliance-method.md`; never as hard-rule source.
- confidence_default: 3

## S-IMP-PRIMARY
- type: `primary`
- location: `references/impressum-legal-source-map.md`
- purpose: Current EU/DE primary-source bindings for hard-enabled Release-1 rules.
- reliability: Primary legal text as verified on 2026-09-08.
- limitations: Applicability still depends on website/business evidence; not legal advice.
- use_in_skill: Legal rule admission and freshness gate.
- confidence_default: 5

## S051 - P0 Customer-Truth authorization for Impressum risk surfacing
- type: `user_provided`
- location: project conversation 2026-09-09
- purpose: Product-level requirement that strongly observed possible or obvious provider-identification / Impressum risks must be explicitly and prominently surfaced to the customer rather than disappearing because legal jurisdiction is unresolved.
- reliability: Authoritative for Pixelkiez product/reporting behavior; not an external legal authority.
- limitations: Does not authorize a definitive legal-violation claim, penalty prediction, automatic GDPR conclusion, or any change to the 48-metric Core score.
- use_in_skill: `scripts/legal_customer_projection.py`, consolidated Legal finding projection, mandatory top-four routing, cover warning, roadmap/closing persistence, omission gate and Golden Regression.
- confidence_default: 5 for the product requirement.

## S052 - P0 Legal Customer Projection implementation evidence
- type: `primary`
- location: current skill source tree (`scripts/legal_customer_projection.py`, `scripts/attach_impressum_findings.py`, `scripts/validate_impressum_projection.py` and related customer/reporting gates)
- purpose: Executable evidence for the implemented separation between legal claim state and customer-risk priority.
- reliability: Direct locally inspected and deterministically executable implementation.
- limitations: Passing local fixtures proves the routing and fail-closed contracts, not the factual legality of an arbitrary live website.
- use_in_skill: Release validation, Bo-Feng-Lin-class regression, score-preservation and customer-omission controls.
- confidence_default: 5 for implemented package behavior; live legal conclusions remain evidence-bound per S-IMP-PRIMARY.

## Branch-aware customer-selection patch sources (27 October 2026)

- `S-BP-001` — User decision in this conversation: use verifiable approved industry weights when available; otherwise retain conservative business-model-aware selection. `type: user_provided`; claim authority: product requirement (5), not empirical industry data (1).
- `S-BP-002` — Canonical installed skill, `scripts/client_story.py`, `references/strategic-relevance-customer-output-contract.md`, 48-metric registry. `type: primary` for current target behavior; inspected and frozen locally; confidence 5 for observed code.
- `S-BP-003` — VibeCheck03 partial patch and associated provided patch order. `type: user_provided / derived`; suitable for intended check coverage and prior implementation state, not proof of production release; confidence 4 for stated requirements, 2 for unverified live status.
- `S-BP-004` — Industry weight availability. `type: uncertain`; `SOURCE_NEEDED`: no verified, approved sector-weight source was found in the inspected installed selection/registry artifacts; default profile catalog is intentionally empty. Never call the six canonical score-category weights sector benchmarks.
