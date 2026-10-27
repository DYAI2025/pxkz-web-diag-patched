# Core Active Measurement Migration v1

## Decision

This document records a **separate active-measurement/scoring migration** for the existing 48-metric Pixelkiez core. It does not rewrite the earlier Core Evidence Binding & Shadow Resolver decision retroactively.

The earlier Shadow design remains historical evidence of a deliberately score-neutral stage. Its invariant was: normalized Measurement Gateway observations remain enrichment and cannot mutate core score rows. This migration adds a new, explicit admission boundary between evidence execution and canonical core rows.

## Non-negotiable invariants

- `assets/measurement-registry.json` remains the authority for the exact 48 metric IDs, metric weights, category weights, score modes and product score anchors.
- `scripts/compute_score.py` remains the canonical aggregation/scoring engine. This migration must not add a friendlier parallel scorer.
- Raw provider payloads never enter the core score path.
- Missing, unavailable, error or conflict evidence never becomes `0`, `false`, `weak`, `blocking` or any other website-quality value.
- Boolean `false` and numeric `0` can be valid measured values when the metric execution contract permits them.
- An execution result does not carry an independently invented numeric score. It may carry only an authorized Pixelkiez product status; admission materializes the numeric anchor from the measurement registry.
- Metrics with `score_mode=external_threshold` require a non-empty runtime threshold source before admission.
- Every scoreable result requires a method, limitation, admissible evidence grade, same-target evidence, authorized source family and at least one evidence reference.
- `UNAVAILABLE`, `ERROR`, `CONFLICT` and `NOT_APPLICABLE` are explicit execution states and are not score admitted.

## Architecture

```text
Authorized observation / measurement
  -> source-family adapter or bounded agent/manual observation
  -> Core Execution Bundle v1
  -> Core Evidence Binding v1
  -> Score Admission Gate
  -> canonical diagnosis metric rows
  -> existing compute_score.py
  -> scored diagnosis report
  -> internal analysis_report reconciliation
  -> customer projection through existing Strategic Relevance / leakage gates
```

The active binding contract is declarative JSON. It is not executable policy code and does not support `eval`, `exec` or arbitrary expressions.

### Evidence source families

The binding contract uses closed source-family values:

1. `PUBLIC_DETERMINISTIC_TECHNICAL`
2. `MEASUREMENT_GATEWAY`
3. `BROWSER_RENDERING`
4. `PERFORMANCE_CWV_LAB`
5. `SEARCH_INDEXING_SERP`
6. `ANALYTICS_SEARCH_CONSOLE`
7. `STRUCTURED_CONTENT_DOM_METADATA`
8. `RULE_BASED_QUALITATIVE_OBSERVATION`
9. `MANUAL_OR_NON_AUTOMATABLE`

A provider result is never scored merely because it belongs to one of these families. It must first be represented by schema-valid, provenance-bearing evidence in the Core Execution Bundle and pass the metric-specific binding/admission checks.

## Contracts and responsibilities

### `assets/core-evidence-bindings.active.v1.json`

Defines exactly one binding for each of the 48 registry metrics. The binding mirrors the registry's authorized weights, score mode, test method, capability, maximum evidence grade and allowed score statuses, and adds the source-family/admission route. The validator rejects drift from the canonical registry.

### `schemas/core-execution-bundle.schema.json`

Defines provider-neutral normalized execution evidence. It separates execution state, measured/observed value, evidence references, evidence grade, source/method, limitation, product status and threshold source. Raw-provider presence must be false.

### `scripts/core_active_measurement.py`

Implements deterministic contract validation, semantic digesting, score admission and canonical metric materialization. It does not collect network data and does not replace source-specific measurement tooling.

### `scripts/materialize_core_metrics.py`

Creates canonical diagnosis metric rows from a validated execution bundle. Numeric metric scores are copied only from the existing registry anchor selected by the admitted product status.

### `scripts/compute_score.py`

Remains protected and unchanged. It performs the canonical category and overall aggregation after the active admission layer has produced valid canonical metric rows.

## Gateway and enrichment boundary

Measurement enrichment and Measurement Gateway rows remain **non-scoring by themselves**. The label `NON_SCORING_ENRICHMENT` still applies to those records and their original pipeline.

A normalized Gateway/enrichment observation may contribute to an active core metric only when a separate Core Execution result explicitly cites it, preserves its provenance/claim boundary, satisfies the metric's binding and is admitted. This is promotion through a controlled contract, not direct provider-to-score injection.

## Qualitative metrics

The existing registry already identifies metric test methods and control bases, including `PIXELKIEZ_PRODUCT_RUBRIC`, presence checks and current-primary-source controls. This migration does not invent new hidden numerical formulas.

For a qualitative metric to be score admitted, a runtime must produce a direct observed result under the declared method and supply one of the existing coarse product statuses (`strong`, `minor_gaps`, `mixed`, `weak`, `blocking`). The admission layer can verify the status is authorized and evidence-bound; it cannot prove that an agent's semantic observation was truthful merely from JSON structure. Therefore fixture PASS is **contract-path proof**, not independent proof of real-world measurement truth.

If a runtime cannot make the observation without guessing, it must use `UNAVAILABLE` or `ERROR`; an LLM estimate is prohibited.

## Release semantics

Two different statements must not be conflated:

- **Contract path ready**: the package has a tested 48/48 schema/binding/admission/materialization/scoring/report path using explicit fixture evidence.
- **Live audit measurement ready**: a concrete audit run has actually collected admissible evidence for the metric under its declared method.

`FULL_48_ACTIVE_PASS` at package-eval level requires the contract path to pass all 48 metrics, mutation tests, determinism, protected-weight checks and report reconciliation. A concrete audit may still have fewer than 48 admitted metrics because unavailable evidence remains unavailable.

No fixture, mock or Shadow artifact may be described as live website evidence.

## Determinism and provenance

Semantic digests canonicalize evidence/results by stable keys and exclude nondeterministic timestamps from the semantic hash. Contradictory duplicate evidence is a conflict, not last-write-wins.

Critical artifacts retain or can derive:

- baseline skill digest;
- measurement-registry digest/version;
- active-binding digest/version;
- execution semantic digest/run ID;
- evidence references and evidence digests;
- score input/output digests;
- internal analysis-report digest.

These receipts support reconstruction. They are not compliance certification.

## Rollback

The migration is additive around the canonical scorer. Rollback removes the active binding/schema/materialization layer and restores the previous canonical report input path. `compute_score.py`, measurement registry, category/metric weights, v1.3 batch contract and renderer remain protected.
