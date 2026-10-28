# Pixelkiez Visualization Template Contract v2

## Normative assets

- catalog: `templates/visualization-catalog.v2.json`
- templates: `templates/visualizations/*.vl.json` and `templates/diagrams/*.mmd`
- schema: `schemas/visualization-plan.schema.json`
- source grammar schema: `assets/vega-lite-schema-v6.4.3.json`
- design reference: `assets/PXK_web_audit_template.pdf`

Vega-Lite is the canonical specification grammar. The PDF consumes rendered SVGs, not ad-hoc drawing commands. The actual SVG backend is recorded as Vega-Lite, Mermaid CLI or `PIXELKIEZ_SVG_FALLBACK`.

## Whitelist

Exactly 15 template IDs are approved: V01-V14 plus D01. See `references/visualization-template-catalog-v2.md`. Arbitrary generated Vega/Mermaid specifications are forbidden.

## Mandatory anatomy

Every selected visual contains:

1. approved template ID;
2. customer-readable title and optional subtitle;
3. metric and/or finding references;
4. data with explicit scope/population;
5. method/source;
6. evidence class;
7. visible `Beweist nicht:` statement.

## Selection and budget

A full customer presentation contains 4-7 visual pages. Core candidates are category bars and exactly four top levers; the overall score appears on the cover, and audit coverage (V12) and the finding count (V11) stay internal-only. Additional visuals are selected only when their required direct data form exists.

The planner records excluded candidates and reasons. Missing input never produces a fabricated chart.

## Benchmark and ranking gate

`V04_FINDABILITY_BENCHMARK` and `V05_RANKING_POSITION` require canonical `benchmark_data` with timestamp, method, location and entities. Rankings additionally require query and integer position. Absence produces explicit exclusion reasons.

## Brand and legibility

- orange = primary series/accent;
- ink = comparison/text;
- sage = context/track;
- numbers/axes = data font;
- SVG text >= 13 CSS px;
- PDF chart-label target >= 10 pt;
- no 3D, word cloud, decorative gauge or radar chart;
- no remote resource, script, `foreignObject`, event handler or external SVG reference.

## Validation

- `validate_visualization_plan.py`
- `render_visualizations.py`
- `validate_visual_assets.py`
- `run_visualization_gallery_evals.py`
- rendered visual QA on the final PDF.
