# Customer PDF QA — fixed probe checklist (review round 4 onward)

Fixed on 2026-10-29 before review round 4, by owner decision ("Fixed probe checklist"), after three adversarial
rounds (11, 18, 12 findings) kept finding new instances of the same class: two customer surfaces reading one
metric differently. A reviewer must report zero confirmed defects **against this list**. Anything outside the
list is logged as backlog with a reason and does not block QA PASS. The list may only change by owner decision,
recorded here with date and reason; it may not be widened or narrowed during a review.

Sources: spec `2026-10-28-pixelkiez-evidence-bound-claims-fix-slice.md` (REQ-F-001…004, REQ-NF-001,
TASK-004/005) and the owner decisions recorded in `2026-10-29-evidence-bound-claims-evidence-ledger.md`.

## A. Claim scope (REQ-F-001, REQ-F-002)
| id | probe | how it is checked |
|---|---|---|
| A1 | Every page of a proof PDF built from example data names "Beispieldaten". | PDF text per page |
| A2 | Example data carries no measurement date or period (round 1: replayed fixture periods read as real). | PDF text: no `\d{4}-\d{2}-\d{2}`, no "dokumentierter Zeitraum", no "Stand" |
| A3 | Lab values are called "Testmessung"; visitor (field) values are worded as visits ("bei 3 von 4 Besuchen"); neither is called "Ladezeit" for LCP. | PDF text vs metric source family |
| A4 | No "Reale …", "Labortest", "Labormessung", "Felddaten", raw metric ids, "p75", process/QA/tool terms. | PDF text |
| A5 | Customer mode refuses every example-data case and writes no PDF. | `cases.json` refusals |

## B. One reading per metric (REQ-F-003, REQ-F-004, REQ-NF-001) — machine-checked
`scripts/validate_customer_surface_consistency.py` runs inside every deliverable build and fails closed. The
reviewer re-checks its result on the PDFs.
| id | probe |
|---|---|
| B1 | Every metric has one customer reading (`scripts/customer_reading.py`): presence-only and present → "(vorhanden) · Nicht belastbar bewertet"; contested by a projected legal/identity risk → "Nicht belastbar bewertet"; otherwise the score status. Matrix rows show exactly that reading (a lever-cited metric may read "Verbesserung sinnvoll" instead of "Klar"). |
| B2 | A strength is shown only if every metric it cites reads "Klar" and no metric of the same declared topic (`assets/customer-topic-overlaps.v1.json`) is a lever metric or reads "Handlungsbedarf". |
| B3 | A "Klar" matrix row is not shown when a metric of the same declared topic is a lever metric or reads "Handlungsbedarf". |
| B4 | No lever's primary (first cited) metric reads "Klar". |
| B5 | No category bar for a category containing a metric contested by a projected legal/identity risk; the chart says that such areas are left out. |
| B6 | The performance threshold page only illustrates one of the four levers. |

## C. Order and priority (TASK-005, owner decision "two orders", "drop P1/P2", "low never outranks medium")
| id | probe |
|---|---|
| C1 | Lever pages say the levers are ordered by business importance; roadmap and closing name the order as "Reihenfolge der Umsetzung". |
| C2 | Roadmap, recommendation next step and closing actions follow one order (audit roadmap timing, then lever rank); every lever appears in the roadmap exactly once. |
| C3 | A critical or mandatory-critical lever is shown as "KRITISCH" and scheduled "Jetzt". |
| C4 | The customer roadmap shows no P1/P2/P3 labels. |
| C5 | A low-severity finding is a lever only when no admissible medium-or-higher finding remains. |

## D. Legibility (WCAG 2.1 SC 1.4.3)
| id | probe |
|---|---|
| D1 | Text contrast ≥ 4.5:1; large text (≥ 18.66 px bold or ≥ 24 px) ≥ 3:1; computed from the CSS/SVG colours on their actual background. |
| D2 | No truncated, clipped or overlapping text; SVG text ≥ 13 px. |

## E. Release-case integrity
| id | probe |
|---|---|
| E1 | The gateway case PDF equals the legacy-baseline PDF; no other two cases are identical. |
| E2 | Each case's levers trace to findings in its own scored input; active-positive findings cite metrics whose status supports them. |

## Backlog (logged, not blocking): layout whitespace, decorative stripe visibility, wording style preferences,
items a reviewer cannot tie to a probe above.
