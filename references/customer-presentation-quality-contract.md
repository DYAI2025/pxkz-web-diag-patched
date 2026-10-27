# Customer Presentation Quality Contract

## Purpose

This contract makes customer-presentation quality non-compensatory and release-bound. A presentation is not final because a PDF exists. It is final only when the same final artifact digest passes deterministic semantic/structural gates and completed page-by-page visual and semantic inspection.

## Quality model

Quality is a vector of hard gates, not an averaged score. One failed hard gate blocks final delivery even when all other gates pass. The canonical machine output is `customer-presentation-quality-report.json`.

The required hard gates are:

1. `artifact_binding` - PDF, client model, scored report, render receipt and both QA manifests refer to the current artifact digests.
2. `score_projection` - customer score display follows the resolved score policy exactly.
3. `cover_integrity` - page 1 contains the full customer, score projection when applicable and complete key message; page-1 visual QA explicitly confirms no clipping, overlap or cross-page sentence split.
4. `four_lever_completeness` - exactly four strategic levers, each with observation, business impact and action.
5. `sentence_integrity` - no truncation marker in customer-visible copy; closing actions are complete and preserve the full approved action instead of arbitrary character clipping.
6. `business_impact_visibility` - the four-lever page renders the business impact, not only the observation and action.
7. `privacy_claim_scope` - no legal/compliance certainty and no blanket `Einwilligungen OK/klar/konform` wording from a surface-only audit.
8. `no_synthetic_priority_magnitude` - ordinal priority visuals may show rank 1-4 but may not invent 100/80/60/40-style magnitude values.
9. `visual_qa` - every final rendered page passes digest-bound visual inspection; page 1 has the additional cover checks.
10. `semantic_qa` - every final page passes semantic comparison with client model and canonical scored audit; overall checks include score correctness, cover completeness, lever impact completeness, privacy scope and no synthetic metric visuals.
11. `page_budget` - customer PDF remains within the contractual page budget.
12. `customer_language_guardrails` - no internal audit/runtime/coverage/QA language leaks into the customer projection.
13. `legal_risk_projection_completeness` - when a bound Impressum sidecar resolves to mandatory customer risk, the same consolidated finding must be present in the diagnosis, selected top four, cover warning, immediate roadmap, closing actions, and final PDF. Omission is release-blocking.

`quality_status=PASS` requires every applicable hard gate to pass. `PENDING_QA` is permitted only as a build-state and must never be presented as final customer output.

## Resolved customer score projection

The historical conflict between the scoring policy and Strategic Relevance policy is resolved as follows:

- `FULL_SCORE`: show numeric value as `Pixelkiez Score`.
- `PARTIAL_SCORE` with the internally valid 50-79% coverage gate: show the numeric value as `Pixelkiez Bewertungsstand`, never as `Pixelkiez Teilscore`; do not show coverage or confidence to the customer. The label makes the limited evidence state explicit without exposing audit-process metadata.
- `NO_SCORE`: show no numeric overall value and lead with the strongest strategically relevant supported finding.

The numeric value remains a proprietary Pixelkiez diagnostic orientation, never an external standard, certification, forecast or universal website-quality score.

## Draft -> inspect -> repair -> re-inspect loop

The first rendered PDF is always a draft. After rendering:

1. render every page to PNG;
2. create PENDING visual and semantic QA manifests;
3. inspect every page against the final client model and scored audit;
4. when any visual or semantic issue is found, repair the source/model/template, re-render, regenerate both QA manifests and inspect the changed final digest again;
5. run `validate_customer_presentation_quality.py`;
6. only a PASS report may be described as final.

A prior PASS is invalid after any material PDF/model/report change because the QA manifests and quality report are digest-bound.

## Proof vs customer release

Quality PASS is independent from the exact-font gate. A proof build can be `QUALITY_PASS_FONT_BLOCKED`. Strict `customer_release_ready=true` additionally requires exact approved runtime fonts. Font fallback never converts a quality failure into PASS.
