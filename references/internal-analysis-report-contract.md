# Pixelkiez Internal Analysis Report Contract

## Purpose

The customer PDF is selective. `analysis_report.json` and `analysis_report.md` are the complete internal consulting record for the same scored audit. They are mandatory for a completed full analysis and are never replaced by the presentation.

## Canonical source and projections

```text
diagnosis-report-scored.json
  -> build_internal_analysis_report.py -> analysis_report.json
  -> render_internal_analysis_markdown.py -> analysis_report.md
```

Both projections bind to the source digest. The Markdown is generated only from the internal JSON; it is not a separately authored interpretation.

## Per-metric completeness

Every metric present in the canonical scored report appears exactly once in both internal reports. Each metric record contains at least:

- metric ID, category and customer-readable label;
- applicability and assessment status;
- raw value and unit;
- Pixelkiez score when the scoring policy permits one;
- canonical metric weight, category weight and the metric's weighted contribution;
- explicit `score_admitted` state so an unadmitted result cannot look scored;
- measurement class and evidence grade;
- confidence;
- method/source and threshold source when present;
- evidence references;
- a bounded interpretation;
- `does_not_prove`;
- action state and linked recommendations/findings, or explicit `NO_ACTION`.

`not_assessed`, `MISSING` and `SOURCE_NEEDED` are preserved. Missing evidence is not converted into a zero, passing value or recommendation.

## Additional complete sections

The reports retain:

- audit metadata and source digest;
- score and coverage state;
- all category summaries;
- findings and recommendation links;
- roadmap;
- complete sources;
- limitations;
- missing/source-needed registers;
- visualizations selected for the customer presentation, with their evidence boundaries.

## Validation

`validate_internal_analysis_report.py` proves source-digest parity, metric ID/count parity, exactly one Markdown anchor and section per metric, source parity and presence of recommendation/action state. It does not claim that a public-only audit measured private analytics or business outcomes.

## Additional legal internal record
When legal assessment is enabled, `impressum-compliance.json` is an additional `INTERNAL_RECORD`. It is digest-bound in the deliverable manifest and is not a customer-score or chart input.
