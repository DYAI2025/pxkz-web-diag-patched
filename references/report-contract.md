# Canonical Report and Deliverable Contract

`diagnosis-report-scored.json` is the factual source of truth for one run. It is projected deterministically into complete internal reports, a constrained customer story, evidence-bound visual specifications and the customer PDF. No projection may create new facts.

## Mandatory distinctions

| Field | Meaning |
|---|---|
| `measurement_class` | measured, observed, inferred risk, or not assessed |
| `evidence_grade` | E1-E8 source/evidence strength class |
| `fact` | evidence-backed statement |
| `inference` | reasoned consequence from facts |
| `recommendation` | proposed action |
| `MISSING` | required information absent |
| `SOURCE_NEEDED` | claim exists but lacks adequate support |

## Three mandatory reporting artifacts

### `analysis_report.json`

Complete internal machine report. It must contain every canonical metric exactly once, plus label, category, value, unit, score, measurement/evidence class, confidence, method/source, threshold source, evidence refs, interpretation, `does_not_prove`, action state and recommendation links. Sources, findings, recommendations, coverage, limitations, missing and source-needed registers are retained.

### `analysis_report.md`

Complete consulting report generated from `analysis_report.json`. Every metric has exactly one stable anchor and section. It is intended for advisory preparation and may be longer than the customer PDF.

### `customer_presentation.pdf`

Selective visual presentation. It shows exactly four supported levers and four to seven evidence-bound visual pages. It does not carry the full technical metric/source register.

## Build graph

```text
diagnosis-report-scored.json
  +-> analysis_report.json -> analysis_report.md
  +-> visualization-plan.json -> specs/SVGs + receipt
  +-> client-report-model.json
  +-> customer_presentation.html -> WeasyPrint -> customer_presentation.pdf
```

`deliverable-manifest.json` binds all outputs by digest. `deliverable-bundle-validation.json` separates `build_complete` from `customer_release_ready`.

## Comparison integrity

Benchmark/ranking charts are valid only when the canonical report includes explicit query/entity, location, method/device and timestamp context. No absent benchmark may be replaced with a remembered or invented industry average.

## Customer release integrity

A rendered PDF is not automatically complete. Customer release requires exact requested fonts, final visual QA PASS and final semantic QA PASS against the same PDF/model/audit digests.

## Batch boundary

The ElevenLabs CSV remains an additive provider adapter from the same audit truth. It does not redefine website evidence or the reporting outputs.
