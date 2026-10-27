# Pixelkiez Diagnostic Score Policy

## Status

The Pixelkiez score is a proprietary diagnostic reference for client orientation. It is not a universal website-quality standard, accreditation, compliance score, ranking prediction, revenue forecast, or conversion prediction.

The policy exists because the user explicitly requires a front-page score. The numeric policy below is a product decision, not an external standard.

## Inputs

Scoring uses only metric records whose IDs exist in `assets/measurement-registry.json`.

A metric can contribute only when all are true:

1. `applicable = true`.
2. Registry defines it as scoreable.
3. `measurement_class` is `measured` or `observed`.
4. `score` is numeric from 0 to 100.
5. `evidence_grade` is E1-E6.
6. `threshold_source` or a product-rubric reference is present.
7. The result includes `does_not_prove`.

`inferred_risk`, `not_assessed`, E7, and E8 never contribute to the numeric score.

## Metric scale

Every scoreable metric uses the same coarse product anchors from `assets/measurement-registry.json`:

- 100: `strong`; no material issue in the tested population.
- 75: `minor_gaps`.
- 50: `mixed`; meaningful friction or incomplete implementation.
- 25: `weak`.
- 0: `blocking` or materially broken in the tested population.

This avoids decimal pseudo-precision at metric level. For metrics governed by an external threshold, first classify the measured raw value against a **current inspected threshold source**, record that source/date, then map the resulting status to the Pixelkiez product anchor. Do not invent an external-to-100 formula.

`compute_score.py` rejects a score that does not equal the registered anchor for its status.

## Category score

For category `c`:

`category_score = sum(metric_score * metric_weight) / sum(metric_weight for eligible scored metrics)`

`category_coverage = sum(metric_weight for eligible scored metrics) / sum(metric_weight for applicable registry metrics)`

Do not treat unassessed metrics as zero quality. They reduce coverage instead.

A category number may be shown only when `category_coverage >= 0.50`. Otherwise show `nicht ausreichend gemessen`.

## Overall quality score

The category weights are defined in `assets/measurement-registry.json` and sum to 100.

Compute the assessed quality score over categories that have a valid category score, renormalized across the assessed category weights. Always show weighted audit coverage next to it.

### Display gate

This gate is a Pixelkiez product policy:

- `coverage >= 80%`: label `Pixelkiez Score`.
- `50% <= coverage < 80%`: internal label remains `Pixelkiez Teilscore`; customer projection uses `Pixelkiez Bewertungsstand` without exposing coverage/confidence.
- `coverage < 50%`: do not show an overall number; show `Score nicht belastbar` and the coverage percentage.

This prevents a visually precise overall score from hiding major evidence gaps.

## Overall interpretation bands

These are Pixelkiez product-language bands, not external standards:

| Score | Client wording |
|---:|---|
| 0-39 | Grundlegender Handlungsbedarf |
| 40-59 | Deutlicher Verbesserungsbedarf |
| 60-74 | Solide Basis, klare Hebel |
| 75-89 | Stark mit gezielten Lücken |
| 90-100 | Sehr stark im geprüften Umfang |

Do not apply the supplied Lighthouse-style 0-49 / 50-89 / 90-100 bands to the overall Pixelkiez score. Those bands belong only to metrics whose official/current source defines them.

## Coverage and confidence

Internal scoring keeps three distinct concepts:

- Quality score or partial score.
- Audit coverage in percent.
- Confidence: High / Medium / Low.

Customer projection follows `references/customer-presentation-quality-contract.md`: FULL_SCORE -> `Pixelkiez Score`; PARTIAL_SCORE -> `Pixelkiez Bewertungsstand`; NO_SCORE -> no number. Coverage and confidence remain internal.

Suggested deterministic confidence mapping:

- High: coverage >= 80% and no scored category depends mainly on E6 evidence.
- Medium: coverage >= 50% with direct measured/observed evidence.
- Low: coverage < 50% or the conclusion depends heavily on proxies.

If the score is hidden because coverage < 50%, confidence cannot be High.

## Blockers

Never average away a high-priority blocker. The score can coexist with a blocker, but the cover and executive summary must carry a visible blocker callout when a `critical` finding has confidence >= 4.

Do not apply an arbitrary score cap unless a future Pixelkiez policy explicitly defines and sources that rule.

## Required output fields

The canonical report must contain the scoring-policy and measurement-registry versions so a score can be reproduced:

```json
{
  "score_summary": {
    "policy_version": "2.0.0",
    "registry_version": "1.0.0",
    "label": "Pixelkiez Score",
    "score": 72,
    "display_status": "FULL_SCORE",
    "coverage_percent": 84,
    "confidence": "HIGH",
    "interpretation": "Solide Basis, klare Hebel",
    "blocker_present": false,
    "does_not_prove": [
      "keine universelle Website-Qualität",
      "kein Ranking-, Umsatz- oder Conversion-Nachweis",
      "keine rechtliche oder WCAG-Konformität"
    ]
  }
}
```

## ILES firewall
ILES uses eight binary-admission dimensions totaling 100. `LIKELY_APPLICABLE`, `CONDITIONAL`, `UNKNOWN`, `inferred_risk`, E5-E8 and unresolved conflicts receive zero. IMP-10 and IMP-11 are modifiers and never double-count. ILES never changes overall score, coverage, score anchors or Core status.
