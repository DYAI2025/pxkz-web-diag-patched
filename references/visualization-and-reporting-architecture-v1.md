# Pixelkiez Visualization and Reporting Architecture v1

## Purpose

The Website Diagnosis produces one validated audit truth and three mandatory product artifacts:

1. `analysis_report.json` - complete machine-readable internal analysis;
2. `analysis_report.md` - complete human-readable consulting report;
3. `customer_presentation.pdf` - concise, chart-led customer presentation.

The PDF is not the complete technical report. The Markdown and JSON are not substitutes for the customer presentation.

## Pipeline

```text
diagnosis-report-scored.json
        |
        +-> build_internal_analysis_report.py -> analysis_report.json
        |                                      -> analysis_report.md
        |
        +-> build_visualization_plan.py -> visualization-plan.json
        |                                -> approved Vega-Lite/Mermaid specs
        |                                -> SVG visual assets + receipt
        |
        +-> build_client_report_model.py -> client-report-model.json
        |                                  (exactly four levers)
        |
        +-> render_diagnosis_pdf.py -> customer_presentation.html
                                      -> customer_presentation.pdf
                                      -> presentation-render-receipt.json
```

The preferred renderer boundary is Vega-Lite-compatible JSON -> SVG -> WeasyPrint HTML/CSS -> PDF. Because ChatGPT/agent runtimes cannot be assumed to have Node, Chromium, `vl2svg`, or Mermaid CLI, every approved template also has a deterministic local SVG fallback. The receipt records the actual backend. A fallback is not relabeled as Vega-Lite execution.

## Engine decisions

- **Vega-Lite: ADOPTED as specification grammar.** Only whitelisted Pixelkiez templates may be instantiated. Arbitrary model-written specs are prohibited.
- **WeasyPrint: ADOPTED as PDF renderer.** It owns page geometry, typography, CSS grid, colors, SVG embedding and PDF output.
- **Mermaid CLI: OPTIONAL.** It may render `D01_PROCESS_FLOW` when available; the skill must remain functional with the safe built-in SVG fallback.
- **fl_chart and Charts/DGCharts: REFERENCE_ONLY.** Their UI patterns informed the comparison, but their Flutter/Swift runtimes are not part of the skill.
- **ReportLab: LEGACY_ONLY.** It is not the default customer presentation renderer.

## Boundary rules

- No chart without metric/finding references, population, method and `does_not_prove`.
- No market benchmark or SERP/ranking chart without query/entity, location, device/method and timestamp context.
- Missing benchmark data produces an explicit excluded-candidate reason, never a fabricated comparison.
- Derived Pixelkiez scores are orientation aids, not measured commercial outcomes.
- All selected visuals are rendered to SVG and must be embedded in the PDF.
- Full audits select 4-7 visuals; the standard synthetic/full fixture selects at least five.
- The top-lever visualization and the findings pages both use exactly four supported levers.
- Visual and semantic QA manifests start `PENDING`. Rendering does not self-certify customer readiness.

## Product states

`BUILT_PENDING_QA` means all deterministic files exist and validate structurally.

`CUSTOMER_RELEASE_READY` additionally requires:

- exact requested display and data font families;
- visual QA PASS against the final PDF pages;
- semantic customer QA PASS against final PDF, client model and scored audit;
- all cross-digests current.

A proof build may use an approved font fallback, but its manifest must keep `customer_release_ready=false`.

## Main command

```bash
python scripts/build_audit_deliverables.py diagnosis-report-scored.json ./deliverables --release-mode proof
```

For a customer release:

```bash
PIXELKIEZ_FONT_DIR=/approved/runtime/fonts \
python scripts/build_audit_deliverables.py diagnosis-report-scored.json ./deliverables --release-mode customer
```

Font files are runtime inputs and must not be bundled into the Skill package.
