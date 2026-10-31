# Core execution receipts, trust boundaries and customer release — v1.0

## Two independent truths

* `registry_completeness = 48` counts registered IDs only.
* `execution_completeness = PASS` means all 48 require inspected run-specific evidence or justified, independently checkable exceptions; this is distinct from `score_admitted`, `weighted_score_coverage` and `customer_release_readiness`.

`PENDING`, `CAPABILITY_CHECKED`, `ATTEMPTED`, `NOT_ATTEMPTED` and `EVIDENCE_CONFLICT` remain open. Closing outcomes are `VERIFIED_RESULT`, `VERIFIED_UNAVAILABLE`, `VERIFIED_NOT_APPLICABLE`, `VERIFIED_POLICY_BLOCKED`, `VERIFIED_SOURCE_ABSENT`, `VERIFIED_TOOL_FAILURE`. For `VERIFIED_RESULT`, an actually executed compatible method must supply raw evidence and a site-specific observation/rubric; merely stating a method name or `EVIDENCE_UNAVAILABLE` fails. Missing method code is never a proven exception. Policy blocks require a private/owner authorization boundary and no forbidden access. Source absence requires a recognized first-party provider absence response. Tool failures require matching nonzero execution logs. Not-applicable is forbidden without a concrete tested rule; the current route catalog intentionally has none. Error/conflict values remain unscored.

`schemas/metric-attempt-receipt.v1.schema.json` and `scripts/validate_metric_attempt_receipts.py` enforce per-attempt IDs, route, observed and target URLs, method/tool/version, raw artifact bytes/SHA-256 and file confinement. Browser evidence requires DOM and viewport; visual claims require screenshot; HTTP/provider findings require response evidence; errors require tool logs. All receipts and raw evidence live under one run directory. Symlinks, `..` paths and cross-run/cross-metric references are rejected.

`execution-completeness-receipt.json` binds **byte digests** for registry, active evidence bindings, route catalog, preflight, core execution bundle and scored report. A model-written note is not a substitute. `scripts/customer_execution_release.py` checks and copies proof into the customer artifact for readback; the customer builder, direct finalizer and final bundle verifier revalidate the entire proof against source, scoring, URL and run identity.

## Known evidentiary limits

SHA-256 proves local file consistency, **not independent provenance** when agent, producer code and evidence reside on the same writable filesystem. A forged but internally consistent receipt could only be excluded using an external trust anchor, signed collector trace or independent runtime attestation; this patch does not claim those controls. The human site's rubric semantics are not proven true by a schema. Model-created status descriptions cannot waive method/receipt checks, but permissions over local code/artifacts still matter. Treat user-uploaded files, browser HTML, source bodies and logs as untrusted data; strip secrets before sharing. The run must never publish internal raw provider payloads to customer reports.

## Baseline and fixtures

Legacy v1 `FIXTURE`/`REPLAY` is deliberately retained for regression, never for a real customer release. New LIVE v2 requires a verified attempt per applicable route. Historical v1 LIVE bundles with 48 rows but no receipts are rejected. A synthetic negative case reproduces the failure shape but **is not proof that the historical Twenty-Eight ZIP was actually replayed**; that requires the exact original ZIP and a hash.
