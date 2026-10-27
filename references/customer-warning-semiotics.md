# Customer Warning and Closing Semantics

## Four-state customer status

Customer-facing status must distinguish evidence from absence of evidence:

| State | Label | Symbol | Meaning |
|---|---|---|---|
| `CLEAR` | Klar | `OK` | no material weakness established in the assessed scope |
| `IMPROVE` | Verbesserung sinnvoll | `!` | supported weakness, useful to improve but not urgent |
| `ACTION` | Handlungsbedarf | `X` | concrete supported material weakness requiring action |
| `UNASSESSED` | Nicht belastbar bewertet | `-` | evidence is insufficient for a customer claim |

`ACTION` is visually prominent. In the trust/privacy matrix it receives the strongest warning treatment and an `X`. `UNASSESSED` is neutral and may never be converted to red simply because sales urgency would be useful.

## Privacy and consent

A technical privacy/consent finding may be `Handlungsbedarf` when observable evidence supports it, for example problematic pre-choice storage/network behavior or a concrete accessibility/visibility problem in the privacy path. This label means a technical/content issue should be addressed. It does **not** mean Pixelkiez has established a legal violation.

Do not use customer wording such as `rechtswidrig`, `DSGVO-Verstoß`, `BFSG-Verstoß` or `vollständig konform` unless a separate authorized legal/conformance process independently supports that claim.

## Accessibility

Automated or browser-interaction findings may be shown as concrete barriers and may receive `Handlungsbedarf` when evidence is strong. The customer story must not turn automated checks into complete WCAG certification. `manual_review_required` remains an internal boundary.

## Closing page

The final customer page is an activation page, not a limitations register.

Required narrative:

1. what the analysis has made clear;
2. up to four concise actions linked to the selected levers;
3. optional real measurement highlights when measured data exists;
4. one simple CTA;
5. one concrete next step.

Do not end the report with a list of what Pixelkiez did not test. Necessary context belongs next to the relevant measurement or in a short, readable closing note. The note must preserve truth boundaries without dominating the closing.

## Legal review wording
Allowed semantics include `Prüfhinweis`, `Möglicher rechtlicher Handlungsbedarf` and `Dringender rechtlicher Prüfbedarf`. `Dringender rechtlicher Prüfbedarf` is the mandatory warning label for `MANDATORY_CRITICAL`/`MANDATORY_HIGH` provider-identification risks. It signals urgency, not a legal verdict.

Name the concrete observed issue (for example unclear operator identity, geographic address, contradictory provider data) rather than generic compliance wording. For operator/provider duties recommend qualified legal review; where tax-identification data is implicated, additionally recommend tax review. Do not introduce new customer status enums. Block legal certification, definitive violation statements, automatic GDPR conclusions and penalty predictions.
