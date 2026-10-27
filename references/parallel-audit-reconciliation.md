# Parallel Audit Reconciliation

Use this reference when the user supplies previous audits, PDFs, crawler exports, PageSpeed/Lighthouse reports, screenshots, or model-generated analyses.

## Process

1. Identify each source and classify it as raw measurement, detailed report, screenshot/observation, user-provided claim, or unsupported conclusion.
2. Extract scores, criteria, methods, claims, evidence, limitations, and date.
3. Re-check the most important current-state claims with direct public evidence when the runtime allows it.
4. Reconcile each material criterion with:
   - previous result;
   - current result;
   - final status;
   - reason for difference;
   - evidence class and confidence.
5. Prefer current direct measurement or reproducible observation over unsupported prior prose.
6. If current verification is impossible, keep the prior claim as `not_verified` or `inferred_risk`, not as fact.

## Score handling

Never average scores from different audits unless their rubrics and scopes are demonstrably compatible. When methods differ, preserve both scores and explain why they are not directly comparable.

## Regression view

For repeat audits, store:

`previous_metric -> current_metric -> change -> evidence -> interpretation`

A changed result is not automatically caused by a website change; tool, sampling, model, device, geography, and timing differences can also explain it.
