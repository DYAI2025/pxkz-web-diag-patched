# Pixelkiez Visualization Template Catalog v2

The canonical machine catalog is `templates/visualization-catalog.v2.json`. All Vega-Lite-compatible source templates are under `templates/visualizations/`; the Mermaid source template is under `templates/diagrams/`.

| ID | Use | Required evidence | Default status |
|---|---|---|---|
| `V01_OVERALL_SCORE` | approved overall Pixelkiez score | score + coverage + scoring policy | core when score allowed |
| `V02_CATEGORY_BARS` | category comparison | at least two scored categories | core |
| `V03_TOP_LEVERS` | four customer priorities | exactly four supported findings | mandatory |
| `V04_FINDABILITY_BENCHMARK` | customer vs documented entities | benchmark entities, method, location, timestamp | conditional |
| `V05_RANKING_POSITION` | query-specific SERP positions | query, position, location, method, timestamp | conditional |
| `V06_QUERY_COVERAGE` | query/intent coverage matrix | query-level measured/observed matrix | conditional |
| `V07_PERFORMANCE_THRESHOLD` | direct value against sourced bands | measured/observed value + sourced thresholds | conditional |
| `V08_AI_ANSWERABILITY` | AI answerability status matrix | at least three assessed AI metrics | conditional/core when available |
| `V09_AGENT_READINESS` | task/capability status matrix | explicit task-level evidence | conditional |
| `V10_TRUST_MATRIX` | trust/content consistency | at least three assessed trust metrics | conditional/core when available |
| `V11_SEVERITY_DISTRIBUTION` | finding distribution | classified findings | lower priority |
| `V12_AUDIT_COVERAGE` | evidence-class coverage | complete metric inventory | core |
| `V13_IMPACT_EFFORT` | action prioritization | evidence-bound impact and effort values | conditional; no invented effort |
| `V14_REPEAT_AUDIT` | before/after comparison | comparable earlier audit | conditional |
| `D01_PROCESS_FLOW` | process/cause/next-step structure | explicit nodes and edges | optional Mermaid/fallback |

## Selection rules

1. Select by data form and decision value, not visual novelty.
2. Prefer directly measured or observed data over derived scores.
3. Do not choose a minor metric merely because it is easy to chart.
4. Use no more than seven visual pages in the customer PDF.
5. Radar, 3D, decorative gauge, word cloud and unsourced benchmark charts are prohibited.
6. A template that lacks required evidence is excluded with a machine-readable reason.

## Styling rules

- Orange `#EC5E43` is the primary series/accent.
- Ink `#0E1414` carries comparison and text.
- Sage colors carry tracks, context and surfaces.
- All numbers and axes use the data-font alias.
- SVG labels are at least 13 CSS px; the PDF chart-label target is at least 10 pt.
- Every visual contains a visible `Beweist nicht:` statement.
