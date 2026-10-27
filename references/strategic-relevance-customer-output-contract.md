# Strategic Relevance & Customer Output Contract

## Purpose

Keep the Pixelkiez audit complete internally while making the customer presentation useful to a business owner. The customer output is not a transcript of the audit process. It is a decision aid about the website, the offer and their business effect.

## North-star question

Before any finding, score, chart, roadmap item or sentence becomes customer-visible, ask:

> Hätte ein Unternehmer, der mit dieser Website oder dem beworbenen Produkt/Service Geld verdient, einen strategischen Vorteil, wenn er diese Information kennt?

If the answer is not clearly yes, keep the information internal.

## Three layers

### Layer 1 - INTERNAL_RECORD

Preserve complete audit transparency for Pixelkiez:

- every canonical metric, including `not_assessed`;
- measurement method, evidence class/grade, source and confidence;
- coverage, score reliability and missing capabilities;
- tool/runtime/validator/QA state;
- enrichment and gateway provenance;
- limitations and open evidence;
- release/build/debug metadata.

This layer feeds `analysis_report.json`, `analysis_report.md`, QA and release evidence. It is never a customer score or customer problem.

### Layer 2 - WEBSITE_BUSINESS_FACT

Contain only assessed website/business conditions supported by evidence. A customer candidate must have:

- at least one linked canonical website metric that is not `not_assessed`;
- traceable evidence;
- a plain-language observation;
- an explicit business impact;
- a practical action.

Missing measurement capability is not a website weakness and cannot create a negative finding or score penalty.

### Layer 3 - CUSTOMER_STRATEGIC_PROJECTION

Select only strategically useful website/business information. A finding must pass the North-star question and materially help with at least one of:

- revenue or inquiry opportunity;
- reach/findability;
- trust or buying confidence;
- usability/contact friction;
- competitive position;
- business risk;
- prioritization or investment decision;
- clear next action.

Exactly four supported levers are preferred for the standard presentation. Do not fill a missing slot with audit-process information.

## Hard customer-output exclusions

Never expose these as customer findings, score factors, chart content, roadmap items or presentation boilerplate:

- Audit Coverage / Messabdeckung / Testabdeckung;
- number of tests, test runs, test series or checked metrics;
- `not_assessed`, `SOURCE_NEEDED`, evidence grades/classes or confidence labels;
- tool, provider, renderer, runtime, fixture, QA, validator, pipeline or release-gate state;
- method/population/debug metadata;
- `Beweist nicht:` boilerplate;
- internal scoring reliability or partial-score labels;
- missing data framed as customer failure.

Measurement context that is itself needed to understand a business fact may remain concise, for example the search query, location/device and date attached to a ranking snapshot. Provider/tool names and internal execution details remain internal.

## Score projection

- Keep `FULL_SCORE`, `PARTIAL_SCORE`, `NO_SCORE`, coverage and confidence internally.
- `FULL_SCORE`: show the numeric value as `Pixelkiez Score`.
- `PARTIAL_SCORE`: show the numeric value as `Pixelkiez Bewertungsstand`; never show the `Pixelkiez Teilscore` label, coverage or confidence.
- `NO_SCORE`: show no numeric overall value and lead with the strongest strategically relevant website finding.
- `not_assessed` metrics never lower the website score.

## Visual projection

- Keep evidence refs, population, method and limitation fields in `visualization-plan.json` and receipts for internal traceability.
- Do not render those internal fields into customer SVG/PDF footers.
- `V12_AUDIT_COVERAGE` is internal-only.
- `V01_OVERALL_SCORE` may exist in the library but is not a separate customer chart page because the full score is already presented on cover/overview.
- Customer chart titles/subtitles must describe the website/business result, not the measurement procedure.

## Roadmap and closing

Build customer roadmap/closing only from the selected strategic levers. Do not backfill it from internal open-evidence lists, missing measurements or generic audit follow-up tasks.

## Public methodology

Pixelkiez may separately publish a general methodology page explaining what the service normally measures. That public transparency is a product/marketing artifact and is not part of an individual customer's diagnosis PDF.

## Validation

A release must pass both:

1. protected-baseline/measurement-platform regression; and
2. customer-output leakage regression across client model, rendered SVG/HTML and PDF.

## Legal finding projection
Validated legal sidecar results use a second evidence route beside Core metrics. A finding is customer-eligible when it carries a schema-valid `customer_risk` from `impressum_compliance`, legal-sidecar evidence, and a supported claim state (`ASSESSED_DEFECT`, `POSSIBLE_LEGAL_REVIEW`, or `CONFLICT`). Do not create fake Core metrics to satisfy this route.

`MANDATORY_CRITICAL` and `MANDATORY_HIGH` legal risks are selected before ordinary website optimization findings. A `MANDATORY_CRITICAL` provider-identity risk must be lever rank 1. Customer language must stay at review/action level and must not expose ILES, applicability internals, expected penalties or definitive legal conclusions.
