# Eval Design

## Purpose

Evals verify the updated Pixelkiez audit contract: Website Intelligence Auditor method coverage, transparent scoring, strict semantic PDF composition, brand consistency, truth discipline, and removal of the PowerPoint branch.

## Trigger coverage

Positive cases must include:

- public business-website audit with branded PDF;
- score/partial-score request;
- search visibility + internal linking + AI extractability review;
- prior-audit reconciliation;
- limited-evidence audit where missing capabilities must reduce coverage.

Negative or near-miss cases must include:

- repository implementation;
- logo-only design work;
- penetration testing/exploit requests;
- legal or WCAG certification;
- generic trend research without a target website;
- PowerPoint-only authoring request.

## Output eval layers

### 1. Evidence and measurement

Require:

- `measured`, `observed`, `inferred_risk`, `not_assessed` separation;
- E1-E8 evidence grade;
- no score contribution from inferred risk, not assessed, E7, or E8;
- explicit unavailable capabilities;
- current primary source at runtime for dynamic thresholds when used.

### 2. Website Intelligence Auditor integration

Require:

- minimum public page sample;
- brand query + site query where tooling exists + at least three relevant non-brand intents;
- crawl/indexability separated from sampled search visibility;
- internal linking / information architecture;
- image/media pipeline;
- content freshness/trust;
- AI extractability/answerability;
- public technology snapshot;
- prior-audit reconciliation when attachments are supplied.

### 3. Score and coverage

Test deterministic cases:

- coverage >= 80% -> `Pixelkiez Score` may be visible;
- coverage 50-79% -> internal `PARTIAL_SCORE`; customer label `Pixelkiez Bewertungsstand` with numeric value, but no coverage/confidence;
- coverage < 50% -> numeric overall score hidden;
- unassessed metrics reduce coverage, never quality by being treated as zero;
- critical high-confidence blocker remains visible regardless of average;
- quality score and audit coverage remain separate.

### 4. Semantic PDF model

Validate the client model against `schemas/client-report.schema.json` and enforce:

- fixed page-section order;
- maximum text lengths;
- exactly six client score categories;
- at most three strengths and three priorities on executive summary;
- top findings contain separate observation / impact / action fields;
- technical evidence and limitations preserved in canonical JSON/model artifacts while the default customer PDF excludes the full technical appendix;
- internal enum labels do not leak into client-facing copy;
- no PowerPoint artifact is required or generated.

### 5. PDF visual QA

For the synthetic fixture:

1. compute score;
2. validate canonical report;
3. build client model;
4. validate client model;
5. render PDF;
6. validate PDF structure/metadata;
7. render all pages to PNG;
8. visually inspect for clipping, overlap, broken glyphs, density, hierarchy, and Pixelkiez brand drift.

A file opening successfully is not enough for visual PASS.

## Failure modes that block release

- fabricated metrics;
- pseudo-precision that hides low coverage;
- dynamic threshold without source;
- unsupported ranking/revenue/conversion/legal/accessibility claim;
- score presented as universal website quality;
- wall-of-text client pages;
- free-form report layout that ignores the validated template;
- generated PPTX or stale PowerPoint pipeline files;
- release report claiming checks that were not actually executed.

## Batch-contract acceptance suite

`scripts/run_batch_contract_evals.py` contains 17 deterministic acceptance cases for v1.3 and regressions:

1. v1/v1.1/v1.2/v1.3 field counts are 82/83/96/96;
2. all 96 v1.3 fields form an exact five-class partition with counts 48/3/18/14/13;
3. a no-context audit export is structurally emitted even while phone-derived runtime fields block upload readiness;
4. a completed audit plus valid phone reaches `EL_UPLOAD_READY` with blank optional email and defaulted unknown prospect;
5. all 13 currently observed agent variables are non-empty through runtime-required/defaulted semantics;
6. missing `PRODUCTION_GATE_ONLY` fields do not block upload readiness and separately keep the production prerequisite gate blocked;
7. authoritative production-only context can pass the separate production gate without changing upload semantics;
8. missing runtime-required phone blocks upload readiness;
9. a runtime-defaulted field left blank after compilation blocks upload readiness;
10. blank `customer_email` never blocks upload readiness;
11. literal `null` remains forbidden, including in optional fields;
12. the shared 96-column v1.2/v1.3 header auto-resolves to the latest v1.3 semantics;
13. explicit v1.2 remains a 96-field compatibility mode;
14. explicit v1.1 remains an 83-field compatibility mode;
15. explicit v1 remains an 82-field compatibility mode;
16. all four versioned simulation fixtures validate against their selected contracts;
17. exact v1.3 cross-skill digest parity is checked only when a sibling Voice Architect v1.3 contract is actually present; otherwise the case reports `NOT_EXECUTED_SIBLING_V1_3_NOT_PRESENT` rather than fabricating parity.

The fixture end-to-end eval also proves that the existing score -> client model -> PDF route still works and that the same scored audit deterministically emits a valid default v1.3 96-field CSV. With only a valid phone number plus audit-owned company evidence, the row reaches `EL_UPLOAD_READY` while optional email/contact data remain blank and the independent `production_prerequisite_gate` remains blocked until authoritative production-only inputs are supplied.

Actual project-level Website Diagnosis -> updated Voice Architect compatibility remains a sibling dependency until the architect implementation exposes the same contract digest/receipt; a local mechanism test must not be relabeled as proof of that external work item.

## Visualization/reporting architecture v1 evals

### Template gallery

`run_visualization_gallery_evals.py` validates every bundled `.vl.json` template against the pinned Vega-Lite schema and fallback-renders all 14 Vega templates plus D01. It validates SVG hashes, palette, minimum labels, `Beweist nicht` and SVG safety.

### Full bundle E2E

`run_reporting_bundle_evals.py` proves on a full scored fixture:

- mandatory PDF + internal JSON + internal Markdown;
- every metric/source exactly once in internal reports;
- four top levers;
- 5-7 selected/rendered/embedded visuals;
- WeasyPrint receipt and no ReportLab default;
- no benchmark/ranking without explicit context;
- deterministic plan/client model;
- font exactness fail-closed;
- visual and semantic manifests remain pending after build;
- unsafe SVG script mutation is rejected.

### Regression boundary

Existing truth-discipline, score, client semantic, v1.3 batch and actual Voice Architect compatibility tests remain mandatory. A visual redesign may not weaken those gates.


## Measurement Platform integration evals

The additive gateway patch must prove:

- protected score/CSV/measurement-platform files remain byte-identical except for an explicit hash-bound allowlist of shared customer-output files required by later Strategic-Relevance or Customer-Presentation-Quality patches; every override must name the frozen baseline hash, current hash and allowed reason;
- gateway envelope schema accepts complete and unavailable fixtures and rejects masquerading fixture/live evidence;
- private, loopback, link-local, metadata-style, credential-bearing and non-default-port targets fail closed before network I/O;
- redirects are re-resolved/revalidated and a rebinding-style second resolution to a private address fails closed;
- identical gateway fixtures normalize deterministically into approved `PUBLIC_*` non-scoring enrichment metrics;
- missing gateway runtime produces an unavailable source state, no synthetic metric values and no score penalty;
- existing measurement-enrichment, score, batch, renderer, visualization and customer-closing regression suites still pass;
- third-party source-code reuse remains false for all four supplied repository snapshots;
- live gateway network evidence is reported separately from fixture correctness.

## Customer-presentation quality regression

`scripts/run_customer_presentation_quality_evals.py` protects the corrected second-pass behavior. It verifies partial-score projection as `Pixelkiez Bewertungsstand`, rejects the old synthetic V03 magnitude, rejects privacy/consent certainty, rejects clipped/fragmentary closing actions, and proves that every four-lever card renders its approved business impact. The rendered proof additionally demonstrates that the first PDF remains `PENDING_QA`, a visible cover defect triggers repair + rerender + full reinspection, and only the exact repaired digest can reach `quality_status=PASS`. Full bundle release requires `validate_customer_presentation_quality.py` PASS after digest-bound visual and semantic QA.

## Active Core 48/48 evaluation

`scripts/run_full_48_active_evals.py` is the contract-path evaluation for the Active Core Migration. It is required in addition to the pre-existing score, Gateway, batch, reporting and customer-quality regressions.

It proves on synthetic fixture evidence:

- exact 48/48 binding and execution set equality;
- evidence-state semantics including valid `false`/`0` values and non-scoreable unavailable/error/conflict states;
- target/source/raw-provider rejection;
- unchanged registry weights and score anchors;
- external-threshold source enforcement;
- independent score recomputation against unchanged `compute_score.py`;
- deterministic results under semantically equivalent input ordering;
- internal analysis-report weighted reconciliation;
- customer-model leakage guard;
- mutation detection for registry, weight, evidence, target, source, score-anchor, threshold and report corruption.

The suite must write the current build-controlled artifact digest into its reports. `validate_full_48_active.py` rejects stale proof reports. The fixture is never live-site evidence.

## Impressum compliance eval layer
Release-1 adds mandatory positive `LEG-P01..P12`, negative `LEG-N01..N12`, six contradiction fixtures, source-freshness tests, no-double-count tests, Core-score-delta=0, customer-overclaim and voice-isolation regressions.

## P0 Impressum Customer-Truth projection evals

`scripts/run_legal_customer_projection_evals.py` protects the non-core Legal -> Customer projection path. It must prove all of the following on the Bo-Feng-Lin-class Golden Regression and negative controls:

- unresolved jurisdiction keeps the legal claim state at `POSSIBLE_LEGAL_REVIEW` and ILES at zero;
- strongly observed operator identity / geographic-address opacity resolves to `MANDATORY_CRITICAL` customer visibility;
- the consolidated Legal finding becomes top-four rank 1 without adding `LEGAL-IMP-*` to the 48-metric Core;
- the warning is visible on cover, four-lever page, immediate roadmap, closing and rendered PDF;
- removing the mandatory Legal finding, cover warning or immediate roadmap action fails closed;
- Core score, coverage and category values remain byte/semantically unchanged for identical Core metric inputs;
- definitive illegality, automatic GDPR conclusions and expected-penalty claims remain rejected;
- the bounded warning phrase `Dringender rechtlicher Prüfbedarf` remains permitted only through the validated Legal customer-risk route.

Release validation treats omission and overclaim as independent hard failures: customer urgency may be high while legal certainty remains explicitly unresolved.
