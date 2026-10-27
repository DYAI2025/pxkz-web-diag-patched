# Agent-Agnostic Compatibility

The core invariants are portable: public read-only scope, evidence before conclusion, fact/inference/recommendation separation, conditional scenarios, fair intervention comparison, traceable JSON, and PDF validation.

Runtime adapters may differ. ChatGPT/Codex may provide browser, web, filesystem, and PDF tooling; other agents may require equivalent user-authorized tools. No cross-model guarantee is made for browsing, screenshots, PageSpeed access, PDF libraries, font rendering, or file delivery.

If the runtime cannot browse or render, stop at a structured evidence request or provide a validated JSON handoff. Do not silently weaken evidence rules.


## Batch-contract portability

The v1 batch contract, CSV builder, CSV/context validators and golden-fixture checks use stable files and deterministic Python behavior. They do not depend on ChatGPT UI or ElevenLabs network access. Other runtimes may reuse them if they provide compatible filesystem/Python execution. Identical platform behavior, provider upload, dialing and downstream agent behavior are not guaranteed.

## Normative PDF-template portability

All compatible runtimes must treat `templates/visualization-catalog.v2.json`, the whitelisted Vega-Lite/Mermaid source templates, `assets/brand-tokens.json`, and the visualization/reporting contracts as one versioned presentation contract. The canonical customer renderer is WeasyPrint; an equivalent runtime may be used only when it preserves the same validated specs, SVGs, fonts, page geometry, digests and QA. ReportLab remains a named legacy rollback path, not an interchangeable default.

A runtime that cannot render and inspect the PDF must not claim the customer PDF is complete. It may stop after validated JSON/chart payloads and hand them to a rendering-capable agent. A completed PDF must carry `pixelkiez-website-analysis.visual-qa.json`, bound to that PDF digest and validated by `scripts/validate_pdf_visual_qa.py`. The validator proves report completeness and digest binding, not the truthfulness of a claimed visual inspection; the named inspector remains accountable for that judgment. Semantic portability does not imply pixel-identical output or identical fonts.

## Active Core Migration portability

The Active Core contracts are file- and Python-based and intentionally avoid agent-specific hidden state:

```text
assets/core-evidence-bindings.active.v1.json
schemas/core-execution-bundle.schema.json
schemas/core-score-admission-report.schema.json
scripts/validate_core_evidence_bindings.py
scripts/validate_core_execution_bundle.py
scripts/materialize_core_metrics.py
scripts/validate_core_score_admission.py
scripts/run_full_48_active_evals.py
```

GPT, Codex, Claude, Claude Code or another runtime may produce the Core Execution Bundle only when it has the source capability and permission required by the metric. Semantic portability does not make missing browser/search/private-analytics capabilities available. A runtime that cannot execute a metric without guessing must emit `UNAVAILABLE`/`ERROR`, not an inferred score.

The 48/48 golden fixture is a deterministic contract test. It must never be reused or described as live website evidence.
