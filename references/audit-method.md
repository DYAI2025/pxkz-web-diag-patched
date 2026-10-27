# Pixelkiez Website Diagnosis Method

## Goal

Produce an evidence-first public website diagnosis that is useful to a non-technical client and defensible to a technical reviewer. The method integrates selected Website Intelligence Auditor capabilities without pretending the skill itself owns every measurement tool.

## Audit modes

Record one mode per run:

- `public_surface`: browser/search/HTTP observations only.
- `measured_public`: public audit plus lab/field/crawler measurements available in the runtime.
- `mixed`: public evidence plus user-provided private exports such as Search Console or Analytics.

Do not call a run `full` merely because many checks were attempted.

## Phase 1 - Scope

Record:

- audited canonical URL and variants;
- customer/company identity and supporting evidence;
- audit date/timezone;
- language/market;
- primary user journey or conversion goal when inferable;
- available and unavailable tools/data;
- sampled page types;
- explicitly excluded surfaces.

Proceed with a public audit when private data is missing. Mark unavailable measurements instead of blocking the whole task.

## Phase 2 - Evidence collection

Follow `references/measurement-contract.md` and `assets/measurement-registry.json`.

Attempt the minimum public audit set, then expand by relevance. Capture evidence before writing findings.

### Public business-contact enrichment for the batch handoff

When a public contact or imprint page explicitly identifies a business contact, managing director, owner, or comparable responsible person, capture the name and role in `public_business.verified_contact` with an evidence pointer. Use it for `prospect_name` only as a verified public business-contact fact; do not infer a personal salutation, preferred call recipient, gender, private contact data, or consent. If no verified person is available, the default v1.3 compiler uses the non-spoken `NICHT_VERIFIZIERT` sentinel for the runtime-defaulted `prospect_name` rather than inventing a name.

Also capture the verified public business display name, audited URL, public business phone when explicitly published, city/category when clear, and the strongest conversation-eligible verified finding. Campaign, lead-source, meeting, consultant-person and compliance authority remain external and are never inferred from the website.

Every metric record must include:

- metric ID;
- applicable yes/no;
- measurement class;
- evidence grade;
- value or observation;
- method/source;
- timestamp when meaningful;
- score only when permitted;
- confidence;
- limitation / `does_not_prove`.

## Phase 3 - Findings

A finding is valid only when evidence is traceable.

Each finding must contain:

- `id`;
- category;
- severity: `critical | high | medium | low | positive`;
- technical observation;
- evidence refs;
- business relevance classified as `fact | inference | recommendation`;
- client-facing observation, impact, and action;
- confidence 1-5;
- owner type;
- horizon;
- acceptance test;
- optional visual evidence asset.

Do not turn a proxy into a causal business claim. Do not infer revenue loss, ranking loss, legal breach, or conversion lift without the required evidence.

## Phase 4 - Score

Run `scripts/compute_score.py` against the metric registry. The score is a Pixelkiez product reference and must always be paired with audit coverage and confidence. Follow `references/scoring-policy.md`.

## Phase 5 - Recommendation

Choose the smallest intervention that addresses the evidence:

- monitor;
- maintenance;
- targeted modernization;
- redesign;
- evidence first.

A redesign is not the default outcome. A healthy site may receive maintenance only.

## Phase 6 - Client narrative

The agent must translate top evidence into concise client language before rendering. Follow `references/pdf-report-contract.md`.

Prefer:

- one clear finding per sentence;
- one consequence per finding;
- one practical action;
- short headlines;
- visible strengths as well as deficits.

Avoid technical vocabulary when a plain equivalent exists. Keep detailed method and evidence in canonical JSON/model artifacts; summarize only the few relevant limits on the final customer limits page.

## Phase 7 - Repeat-audit reconciliation

When a prior audit exists, follow `references/parallel-audit-reconciliation.md` and explain meaningful differences. Never silently overwrite a prior score or claim.

## Phase 8 - Render and verify

Produce:

1. `diagnosis-report.json`;
2. `client-report-model.json`;
3. `pixelkiez-website-analysis.pdf`.

Run all validators. Render the PDF to images and inspect every page before delivery.

## Non-core Impressum compliance step
For public audits, collect the defined legal discovery scope and normalize website observations before classification. Run jurisdiction -> business context -> applicable regimes -> applicability -> evidence admission -> defect classification. Produce `impressum-compliance.json` as an internal sidecar. Do not map legal sidecar states into Core metric rows or score inputs.
