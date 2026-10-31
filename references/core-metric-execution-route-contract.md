# Core 48 Metric Execution Route Contract — Patch A v1.0

## Truth and scope

`assets/metric-execution-routes.v1.json` is the machine-readable route catalog. Exactly one entry exists for each ID in `assets/measurement-registry.json`; `scripts/validate_metric_execution_routes.py` checks capability, evidence-binding, source-family, measurement class, explicit implementation state, fallback limits and route uniqueness. The catalog is *not* proof that any method ran or that it can support a score.

Each route defines `primary`, zero–three semantically distinct `alternatives`, method/version, `adapter`, measurement class, source family, permission, expected input, limits, and `implementation_status`. The `unavailable_fallback_slots` object accounts for every absent alternative. A method with `MISSING_CORE_ADAPTER`, `PARTIAL_RAW_ONLY`, `EXISTING_NONCORE_ONLY`, `MISSING_AXE_OR_BRIDGE` or `AUTH_REQUIRED_NONCORE_ONLY` must not independently close a LIVE metric as measured. `PARTIAL_RAW_ONLY` can supply raw observable input for a separate evaluated rubric but is not itself a score. For `FIND-02`, `UX-08`, `A11Y-01` and `A11Y-04`, explicitly recorded implementation gaps prevent a generic homepage capture from masquerading as an appropriate metric-specific test.

`PERF-01` is **field data** only. `PERF-02/03` are **lab data**, with PSI API primary and local Lighthouse CLI as optional fallback. An API 429 cannot authorize inventing field data; a locally captured Lighthouse report never becomes a CrUX p75. Existing non-core adapters may be reused only where their actual output and permissions match the Core method.

## Live sequence (run-scoped and failure-closed)

1. Run `python scripts/validate_metric_execution_routes.py .` against the skill directory.
2. Run `python scripts/run_48_core_metrics.py --target https://example.org/ --output /safe/run/path` in an authorized environment. Optional `--allow-api` enables existing provider adapters only when a legitimate credential is configured at runtime; `--allow-lighthouse` allows installed CLI. Without the required tools or DNS, the run remains unfinished.
3. Inspect `capability-preflight.json` and `execution-run-summary.json`. Every one of 14 capabilities reports `installed`, `invocable`, `authorized`, `verified_success`; no `verified_success` without a success receipt.
4. Validate receipts: `python scripts/validate_metric_attempt_receipts.py . /safe/run/path`.
5. Check completion: `python scripts/validate_audit_execution_completeness.py . /safe/run/path --scored-report /safe/scored-report.json`. A receipt is only a PASS when 48 obligations have independently verified closing states, not merely 48 rows.
6. Only then use canonical `scripts/core_active_measurement.py` admission/materialization, `scripts/compute_score.py`, strategic prioritization, `build_audit_deliverables.py --release-mode customer --execution-run-dir /safe/run/path`, QA and finalizer. Customer builder requires a completed LIVE receipt from **the same scored-report bytes and audit target**.

`--offline` is an explicitly incomplete test/preflight mode; it is never a customer release. Do not repair a run by editing or inventing receipts, filling missing values with 0/false, or relabeling errors. Restart with a new run ID after an uncertain execution; a fully authenticated resume protocol is not yet implemented.

## Implementation gaps and efficiency

Method registration does not imply collector availability. `IMPLEMENTATION_GAP` is open/PENDING. The existing site-scoped cache can reuse identical, verified HTTP, DOM and source-response bytes for distinct methods *if their evidence type and scope actually match*. `FIND-02` currently requires its own robots/sitemap method, not a reused homepage; keyboard testing cannot be inferred from a screenshot. There is no claimed full live 48/48 coverage in this patch until those gaps are closed or genuine authorized, proven exceptions are obtained.

Permission boundary: public read-only, no form submission, private endpoint, authentication bypass, paid operation, exploitation or credential persistence. The URL resolver rejects non-public DNS addresses; this is not a complete anti-SSRF guarantee across every browser subrequest or DNS rebinding condition. Hardening and real network verification remain separate deployment prerequisites.
