# Pixelkiez Visualization and Internal Reporting Architecture v1 Plan

Plan path: `docs/plans/2026-08-29-pixelkiez-visualization-report-architecture-v1.md`
Status: ready-for-execution
Owner/Executor: coding agent + visual/semantic reviewer + code reviewer
Last updated: 2026-08-29

<!-- GOAL_START -->
Goal: Brandtreue Visual-Pipeline und vollständige interne Auditberichte

Ziel. `pixelkiez-website-diagnosis` erzeugt aus einem kanonischen, gescorten Audit drei verbindliche Produktartefakte: einen vollständigen internen JSON-Bericht, einen daraus deterministisch erzeugten Markdown-Bericht und eine kurze, visuelle, brandtreue Kunden-PDF. Daten werden bevorzugt über freigegebene Charts visualisiert; qualitative Probleme bleiben kurze, natürliche Aussagen. Die PDF wird über HTML/CSS und WeasyPrint aufgebaut, Vega-Lite dient als deklarativer Chart-Spec-Contract, Mermaid nur als optionaler Diagramm-Renderer; ein eingebauter SVG-Fallback verhindert chartlose Ausgaben bei fehlender externer Runtime.

Scope. Änderungen im installierten Website-Diagnosis-Skill: Output-Contract, Internal-Report-Builder, Visualization Planner, Vega-Spec-Templates, SVG/optional Mermaid Renderer, WeasyPrint-Presentation-Renderer, Brand-/Font-Gates, End-to-End-Builder, QA, Evals, Release, Provenienz, Packaging und Installation. Der v1.3-CSV-/Voice-Contract sowie kanonische Audit- und Truth-Discipline-Semantik bleiben unverändert.

Bedingungen (hart).
- `analysis_report.json`, `analysis_report.md` und `customer_presentation.pdf` sind bei vollständiger Analyse Pflicht.
- Jede Registry-Metrik erscheint im internen JSON und Markdown genau einmal mit Wert/Status, Messklasse, Evidenzgrad, Methode, Einordnung und Grenze.
- Der Agent wählt nur freigegebene Visual-Templates; freie, unvalidierte Chart-Specs sind verboten.
- Zahlen/Benchmarks/Rankings werden nur aus kanonischer Evidenz dargestellt; fehlende Benchmarkdaten erzeugen keinen erfundenen Vergleich.
- PDF-Layout nutzt ausschließlich Brand-Tokens, Mindestschriftgrößen und WeasyPrint. Ein Font-Fallback wird als degradiert ausgewiesen und darf nicht als exakte Brandfont-Parität gelten.
- Jede ausgewählte Visualisierung erhält SVG, Spec/Source, Datenreferenzen, Backend-Receipt und visuelle QA.

Akzeptanzkriterien.
- Ein E2E-Fixture erzeugt alle drei Pflichtartefakte plus Visualization Plan und mindestens vier sinnvolle Visuals.
- Alle freigegebenen Chart-/Diagramm-Templates bestehen Gallery-, Schema-, SVG- und PDF-Embed-Tests.
- PDF-Fonts, Schriftgrößen, Farben, Seitengröße, SVG-Anzahl und Brand-Tokens werden deterministisch validiert.
- Metrikvollständigkeit ist zwischen Registry, kanonischem Report, internem JSON und Markdown nachweisbar.
- Fehlende Ranking-/Branchenvergleichsdaten führen zu `NOT_AVAILABLE`, nicht zu synthetischen Werten.
- Bestehende Truth-, v1.3-, Pair-, Score-, Semantic- und Release-Regressions bleiben grün.
- Enterprise Code Review des finalen Snapshots enthält keine offenen Blocker/Critical Findings.

Explizit out-of-scope.
- Beschaffung von Google-Ranking-, Wettbewerber- oder Branchenbenchmarkdaten ohne separate Messquelle.
- Übernahme von Swift/DGCharts oder Flutter/fl_chart als Runtime-Abhängigkeit.
- Einbetten oder Weitergeben lizenzierter Fontdateien im Skill-Paket.
- Interaktive Web-Dashboards, Animationen oder 3D-Charts.
- Änderung der 96 v1.3 CSV-Felder oder der Voice-Agent-Gesprächsstrategie.

Done-Definition. Der final installierte Skill erzeugt die drei Pflichtartefakte aus demselben Audit-Digest, rendert freigegebene Charts über die dokumentierte Backend-Kette, besteht Brand-, Visual-, Semantic-, Completeness-, Legacy-, Release- und Ledger-Gates, wird als exakt `skill.zip` paketiert und erhält einen snapshot-gebundenen Enterprise Code Review ohne offene Blocker/Critical Findings.

Reference-Doc: `references/visualization-and-reporting-architecture-v1.md`
<!-- GOAL_END -->

## Evidence and source boundary

### Inspected facts
- Der aktuelle Skill nutzt ReportLab und zeichnet V01-V11 selbst; WeasyPrint ist in der lokalen Laufzeit verfügbar.
- Die Brand-Tokens nennen Schibsted Grotesk und IBM Plex Mono, markieren die Font-Binaries aber als `NOT_BUNDLED`.
- Der aktuelle Kundenreport erzwingt zwei bis drei Charts, besitzt jedoch keinen extern validierten Vega-/SVG-Renderpfad und keinen verpflichtenden vollständigen Markdown-Bericht.
- Der v1.3-/Truth-/Pair-Contract ist bereits implementiert und bleibt eine Regression Boundary.
- Vega-Lite stellt einen deklarativen JSON-Spec-Ansatz sowie SVG/PNG/PDF-CLI-Pfade bereit; WeasyPrint ist ein HTML/CSS→PDF-Renderer; Mermaid CLI rendert deklarative Diagramme; Charts/DGCharts und fl_chart sind native Swift-/Flutter-Libraries und werden nicht als Runtime gewählt.

## Assumptions, missing information, open questions, blockers

### ASSUMPTION
- Die kleinste robuste Architektur ist ein Whitelist-System mit Vega-Lite-Specs plus deterministischem eingebautem SVG-Fallback; dadurch bleibt die Ausgabe unabhängig von Node-/Chromium-Verfügbarkeit.
- Vier bis sechs datengetriebene Visuals reichen für die normale Kunden-PDF; zusätzliche Metriken bleiben im internen Bericht.

### MISSING
- Vollständige Schibsted-Grotesk- und IBM-Plex-Mono-Fontdateien sind nicht im Skill gebündelt und dürfen nicht als User-Artefakt verteilt werden.
- Eine kanonische externe Ranking-/Benchmark-Datenquelle ist nicht Teil dieser Repositories.

### SOURCE_NEEDED
- Echte Branchenvergleichswerte und Google-Rankings benötigen eine separate, query-/zeit-/ort-/gerätegebundene Messquelle.

### BLOCKER
- Kein Blocker für die Architekturimplementierung. Exakte Brandfont-Parität eines konkreten Kunden-PDFs bleibt jedoch `BLOCKED_FONT_BINARY` oder `DEGRADED_APPROVED_FALLBACK`, bis die Produktionslaufzeit die Fonts rechtmäßig bereitstellt.

## Options considered

| Option | Nutzen | Kosten/Risiko | Entscheidung |
|---|---|---|---|
| ReportLab weiter ausbauen | wenig Migration | eigene Chart-/Layout-Engine, hohe Drift, schwerer Font-/CSS-Contract | verwerfen als Default; Legacy-Renderer nur Rollback |
| Vega-Lite + WeasyPrint ohne Fallback | fachlich sauber | Node/vl-convert kann in Skill-Runtimes fehlen; chartlose oder blockierte Ausgabe | nicht robust genug |
| Vega-Lite-Spec + eingebauter SVG-Fallback + WeasyPrint | deklarativ, reproduzierbar, offline-fähig, SVG-first | begrenzte Whitelist muss selbst gepflegt werden | **gewählt** |
| Flutter/fl_chart oder Swift/DGCharts Runtime | hochwertige native Charts | zusätzlicher SDK-/Capture-/Rasterpfad, falscher Stack | nur Designreferenz |
| Mermaid als Universalrenderer | einfacher DSL | quantitative Charts schwächer | nur D01/D02 Spezialdiagramme |

## Requirements

| ID | Type | Requirement | Source | Verification |
|---|---|---|---|---|
| REQ-F-201 | Functional | Full-run emits PDF + JSON + Markdown | user-provided | E2E artifact test |
| REQ-F-202 | Functional | Visualization Planner selects only approved templates | architecture | plan schema + negative tests |
| REQ-F-203 | Functional | At least four truthful visuals for full eligible fixture | user-provided | E2E and PDF checks |
| REQ-F-204 | Functional | HTML/CSS/WeasyPrint is default presentation path | chosen architecture | renderer receipt |
| REQ-F-205 | Functional | Optional Mermaid only for flow/timeline/cause-effect | repo audit | backend tests |
| REQ-D-201 | Data | Every registry metric appears once in internal JSON/MD | user-provided | cross-artifact completeness validator |
| REQ-D-202 | Data | Each metric has value/status, class, grade, method, interpretation, limitation | user-provided | schema validator |
| REQ-D-203 | Data | Chart values reference canonical metric/finding/category IDs | truth discipline | provenance validator |
| REQ-D-204 | Data | Missing benchmarks/rankings remain explicit | source policy | negative fixtures |
| REQ-A-201 | Architecture | Vega-Lite JSON is chart-spec contract | repo selection | spec/schema validation |
| REQ-A-202 | Architecture | SVG is the interchange format into WeasyPrint | repo selection | file receipts + PDF embed |
| REQ-A-203 | Architecture | Built-in SVG renderer is bounded to template whitelist | reliability | gallery tests |
| REQ-A-204 | Architecture | ReportLab renderer retained only as explicit legacy rollback | migration | source/CLI inspection |
| REQ-NF-201 | Brand | Requested brand fonts or explicit degraded fallback receipt | brand contract | font resolver + PDF font inspection |
| REQ-NF-202 | Brand | Minimum font sizes and approved palette enforced | user-provided | PDF span/CSS/SVG validator |
| REQ-NF-203 | Reliability | No chart page may be empty, clipped, overlapping or unlabeled | user-provided | render + visual QA |
| REQ-NF-204 | Portability | No network is required for normal render | enterprise constraint | offline E2E |
| REQ-S-201 | Security | Untrusted HTML/URLs are never fetched by WeasyPrint | WeasyPrint boundary | safe URL fetcher tests |
| REQ-O-201 | Operations | Every render writes backend/digest/font receipts | enterprise | receipt schema/validation |
| REQ-O-202 | Release | New evidence epoch after final non-report freeze | existing ledger | pipeline ledger |

## Architecture and file boundaries

### Target architecture

```text
scored diagnosis report
    ├── build_internal_analysis_report.py
    │      ├── analysis_report.json
    │      └── analysis_report.md
    ├── build_client_report_model.py
    └── build_visualization_plan.py
           └── visualization-plan.json
                  ├── approved Vega-Lite specs
                  ├── optional Mermaid source
                  └── render_visualizations.py
                         ├── *.vl.json / *.mmd
                         ├── *.svg
                         └── visualization-render-receipt.json

client model + visualization plan + SVGs + brand tokens
    └── render_diagnosis_pdf.py (WeasyPrint)
           ├── customer-presentation.html
           ├── customer_presentation.pdf
           └── presentation-render-receipt.json
```

### File boundaries

### Create
- `references/visualization-and-reporting-architecture-v1.md`
- `references/visualization-template-catalog-v2.md`
- `references/brand-rendering-contract-v2.md`
- `references/upstream-visualization-source-notes.md`
- `schemas/internal-analysis-report.schema.json`
- `schemas/visualization-plan.schema.json`
- `schemas/visualization-render-receipt.schema.json`
- `schemas/presentation-render-receipt.schema.json`
- `templates/visualizations/*.vl.json`
- `templates/diagrams/*.mmd`
- `templates/presentation.html.j2`
- `assets/presentation.css`
- `assets/vega-lite-schema-v6.4.3.json`
- `assets/upstream-visualization-snapshots.json`
- `scripts/build_internal_analysis_report.py`
- `scripts/build_visualization_plan.py`
- `scripts/render_visualizations.py`
- `scripts/visual_svg_renderer.py`
- `scripts/render_presentation_html.py`
- `scripts/build_audit_deliverables.py`
- `scripts/validate_internal_analysis_report.py`
- `scripts/validate_visualization_plan.py`
- `scripts/validate_visualization_assets.py`
- `scripts/validate_presentation_brand.py`
- `scripts/validate_deliverable_bundle.py`
- `scripts/run_visualization_gallery_evals.py`
- `scripts/run_reporting_bundle_evals.py`
- `evals/fixtures/visualization-gallery-data.json`

### Modify
- `SKILL.md`
- `references/report-contract.md`
- `references/chart-template-contract.md`
- `references/pdf-report-contract.md`
- `references/eval-design.md`
- `references/source-map.md`
- `references/security-and-tools.md`
- `assets/brand.json`
- `assets/brand-tokens.json`
- `templates/chart-library.v1.json` or replace with versioned v2 catalog while preserving v1 compatibility
- `scripts/render_diagnosis_pdf.py`
- `scripts/validate_pdf_output.py`
- `scripts/quick_validate.py`
- `scripts/package_skill.py`
- release/evaluation/provenance reports after final freeze

## Implementation phases

## Tasks

### Phase 0 - Baseline and RED tests

### TASK-201: Freeze baseline and encode current defects
- Snapshot installed tree and existing output.
- Add failing tests for missing Markdown report, missing visualization plan/assets, ReportLab default renderer, absent font receipt, fewer than four visuals and absent brand validation.
- Expected: RED for the intended reasons only.

### Phase 1 - Complete internal reporting

### TASK-202: Build canonical internal analysis report
- Implement schema and deterministic builder.
- Join each registry metric with run value/status, interpretation, evidence/method, linked findings and recommended action.
- Preserve `not_assessed`, `MISSING`, `SOURCE_NEEDED` and `does_not_prove`.
- Generate Markdown only from the validated internal JSON.

### TASK-203: Validate metric completeness and traceability
- Assert registry count, IDs, uniqueness and value parity in JSON and Markdown.
- Negative tests for dropped metric, duplicated metric, altered value and unsupported recommendation.

### Phase 2 - Visualization template system

### TASK-204: Curate template catalog
- Create 12-15 approved templates from the adopted architecture: score bullet, category bars, top-four priorities, findability query coverage, ranking dot plot, performance actual/target, answerability heatmap, readiness/trust matrices, severity stack, coverage stack, impact/effort, repeat-audit trend and roadmap flow.
- Specify applicability, required fields, fallback and prohibited claims per template.

### TASK-205: Implement deterministic Visualization Planner
- Select by data form and decision relevance, not aesthetics.
- Require provenance refs and eligibility checks.
- Block benchmark/ranking templates without explicit data.
- Full eligible fixture selects at least four visuals; low-data fixture may select fewer and records `MISSING_VISUAL_DATA` rather than inventing data.

### TASK-206: Render specs and SVGs
- Emit valid Vega-Lite specs for quantitative templates.
- Try approved Vega runtime when present; otherwise render via bounded built-in SVG implementation.
- Emit Mermaid source for D01/D02 and use `mmdc` only when present; otherwise use bounded SVG diagram fallback.
- Record backend, input/output digest, dimensions, fonts and fallback reason.

### TASK-207: Run all-template gallery
- Render every approved template with fixture data.
- Validate XML/SVG structure, non-empty marks/text, palette, dimensions and source/spec receipts.
- Render contact sheet and inspect it.

### Phase 3 - WeasyPrint brand presentation

### TASK-208: Build HTML/CSS presentation system
- Create A4-landscape page components, cover, executive page, category overview, top-four levers, chart pages, roadmap and limits.
- Embed SVGs; no raster screenshot path.
- Use central CSS variables generated from brand tokens.

### TASK-209: Implement font and brand gate
- Detect requested fonts with fontconfig.
- Customer release mode requires exact font family; development mode may use approved fallback only with `DEGRADED_APPROVED_FALLBACK` receipt.
- Never bundle font binaries.
- Validate actual PDF font names, minimum span sizes, palette and SVG label sizes.

### TASK-210: Secure WeasyPrint resources
- Use local-only URL fetcher.
- Reject HTTP(S), file traversal and undeclared assets.
- Test malicious/untrusted resource references fail closed.

### Phase 4 - Unified output builder

### TASK-211: Build all deliverables from one command
- `build_audit_deliverables.py <scored-report> <out-dir>` creates internal JSON/MD, client model, visualization plan/specs/SVGs, HTML, PDF and receipts.
- Fail atomically; incomplete output is not marked complete.

### TASK-212: Validate complete deliverable bundle
- Cross-check source digest across all outputs.
- Require three product artifacts and visualization/brand receipts.
- Require visual and semantic QA manifests before final customer completion.

### Phase 5 - Inspect-and-adapt loop

### TASK-213: Render realistic full and partial fixtures
- Full fixture: >=4 meaningful visuals and complete internal report.
- Partial fixture: explicit unknowns, no invented benchmark/ranking.
- Render pages at 200 DPI and inspect typography, overlap, chart labels and hierarchy.
- Correct template/data/layout defects and rerun until no material visual defect remains.

### TASK-214: Preserve existing contracts
- Run Truth 8/8, v1.3 batch, paired Voice, score/coverage, semantic customer, installability and core parity regressions.

### Phase 6 - Release and final Code Review

### TASK-215: Release, evaluator and provenance
- Update source map, capability decision, architecture gate and core preservation.
- Freeze final non-report tree.
- Generate release report, enterprise evaluator XML, validation report and hash-chain ledger for the exact digest.

### TASK-216: Enterprise Code Review
- Snapshot final skill.
- Review correctness, security, architecture, dependency/license, data contracts, rendering, tests, portability and operations.
- Run deterministic countertests and generate Markdown/JSON/SARIF.
- Any Blocker/Critical triggers patch + new snapshot + re-review.

### TASK-217: Package and install
- Package exact `skill.zip` after PASS.
- Verify one root, required files, no font binaries, no node_modules, no intermediate outputs.
- Install into `/home/oai/skills/pixelkiez-website-diagnosis` and rerun install smoke/E2E.

## Validation strategy

### Validation commands

```bash
python scripts/validate_plan.py docs/plans/2026-08-29-pixelkiez-visualization-report-architecture-v1.md
python scripts/run_visualization_gallery_evals.py .
python scripts/run_reporting_bundle_evals.py .
python scripts/validate_internal_analysis_report.py analysis_report.json analysis_report.md diagnosis-report-scored.json
python scripts/validate_visualization_plan.py visualization-plan.json diagnosis-report-scored.json
python scripts/validate_visualization_assets.py visualization-plan.json visualization-render-receipt.json visuals/
python scripts/validate_presentation_brand.py customer_presentation.pdf presentation-render-receipt.json
python scripts/validate_deliverable_bundle.py output-dir/
python scripts/run_truth_discipline_evals.py .
python scripts/run_batch_contract_evals.py .
python scripts/validate_paired_release.py .
python scripts/run_score_gate_evals.py .
python scripts/run_customer_semantic_evals.py .
python scripts/validate_release_gate.py .
python scripts/validate_pipeline_ledger.py .
python scripts/package_skill.py . ./dist
```

## Inspect-and-adapt gates

1. **Data Gate:** no metric loss or value drift.
2. **Chart Gate:** every selected chart has truthful data refs and a rendered SVG.
3. **Brand Gate:** requested fonts exact or explicit degraded/blocking status; no silent substitution.
4. **PDF Gate:** >=4 visuals for eligible full fixture, no clipping, minimum font sizes, consistent palette.
5. **Internal Report Gate:** every metric once in JSON and Markdown.
6. **Regression Gate:** all pre-existing Truth/v1.3/Voice/score/semantic gates pass.
7. **Review Gate:** no open Blocker/Critical in final snapshot review.

## Rollback and safety

- Keep the prior installed directory and `skill.zip` as immutable rollback baseline.
- Retain the old ReportLab renderer as an explicitly named legacy file during migration; never use it silently in the default path.
- Do not package font binaries, node_modules, repository ZIPs or generated customer data.
- Do not make network requests during standard rendering.
- Do not claim external rankings, benchmarks, legal compliance or commercial effect without evidence.

## Execution handoff

Start with TASK-201 and maintain WIP=1 phase. Record RED evidence before production changes. After any material non-report change, invalidate prior release/evaluator/ledger evidence. Install only the exact reviewed ZIP.

## Plausibility and truth self-check

- Goal block is under 4000 characters.
- File paths are based on inspected current skill structure; new paths are explicitly planned.
- Current Vega-Lite/WeasyPrint/Mermaid capabilities were source-inspected; upstream repositories were not fully built in this run.
- The chosen architecture avoids mandatory Swift, Flutter, network and Chromium dependencies.
- Strongest counterargument: maintaining a built-in SVG fallback duplicates a subset of rendering logic. It is accepted because the runtime must never silently return a chartless PDF when Vega/Mermaid binaries are absent; the whitelist and gallery tests bound this cost.
- Failure chain: missing runtime -> skipped charts -> text-heavy PDF -> false visual-QA PASS. Mitigation: mandatory SVG fallback, asset receipts and minimum-visual gate.
- Bias risks: tool bias toward Vega-Lite, overengineering through too many templates, and false confidence from structural tests. Controls: bounded catalog, realistic rendered QA and explicit font/runtime status.
- Final readiness: ready-for-execution.
