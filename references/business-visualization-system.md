# Pixelkiez Business Visualization System

## Purpose

Translate canonical audit truth into customer-facing business visuals without exposing internal test, coverage, evidence-grade, validator, tool or QA language.

## Approved business visual classes

- `BIG_NUMBER`: one decision-relevant numeric value.
- `BULLET_BAR`: one value against a legitimate, sourced target.
- `HORIZONTAL_BAR`: several directly comparable values.
- `RANKING`: query-bound observed search positions.
- `BENCHMARK`: comparable entities measured under the same documented method/context.
- `STATUS_MATRIX`: categorical or yes/partial/no business facts.
- `EVIDENCE_COMPARE`: concrete page/content comparison when two observed states are useful.
- `PRIORITY_MATRIX`: action priority using evidence-bound impact/effort values only.
- `SHORT_TEXT`: fallback when a truthful chart would require invented numbers.

## Customer-language boundary

Do not render in the customer PDF: coverage, Messabdeckung, Testumfang, Prüfverfahren, evidence grades, measurement classes, confidence labels, internal IDs, validators, QA state, tool names, `not_assessed`, `SOURCE_NEEDED`, fixture/simulation terminology, contract versions or pipeline state.

The internal JSON/Markdown reports retain these fields.

## Routing principles

1. Quantitative facts receive an explicit visual decision.
2. Do not create synthetic numbers for qualitative findings.
3. Ranking requires query, market/location and timestamp; device/method context stays internal unless needed to avoid misleading interpretation.
4. Benchmark requires comparable subjects and identical measurement basis.
5. `V12_AUDIT_COVERAGE` is internal-only and may never be selected for the customer presentation.
6. Customer pages explain the business implication and concrete action; the renderer does not invent either.
