# Pixelkiez Measurement Platform Integration Plan

Plan path: `docs/plans/2026-08-30-pixelkiez-measurement-platform-integration.md`
Status: ready-for-execution
Owner/Executor: coding agent + security reviewer + product reviewer
Last updated: 2026-08-30

<!-- GOAL_START -->
Goal: Build a safe measurement gateway for Pixelkiez website intelligence

Ziel. Extend Pixelkiez Website Diagnosis with reproducible public, owner-authorized, continuous, post-instrumentation, and experimental AI measurements without turning the skill package into a multi-runtime monolith. Preserve the current canonical analysis, business-first presentation, four-lever advisory path, PDF renderer, ElevenLabs v1.3 contract, truth discipline, and all existing release gates.

Scope. Create a separate provider-neutral Pixelkiez Measurement Gateway and integrate it through a versioned measurement-envelope contract. Start with public read-only probes inspired by selected Web-Check capabilities and CSP rule patterns. Add optional adapters for continuous monitoring and first-party analytics only after separate permission, license, and operational gates.

Bedingungen (hart).
- Re-read and freeze the newest installed Pixelkiez baseline before editing; protect all parallel patches.
- Do not bundle full PHP, Go, Java, or Node applications into `skill.zip`.
- Do not copy third-party code before a file-level license and notice decision.
- All network probes are read-only and fail closed against SSRF, private networks, unsafe redirects, excessive responses, and unbounded concurrency.
- Missing credentials or unavailable owner data never reduce the customer score.
- Provider raw data cannot directly create customer claims; it must pass normalization and evidence gates.

Akzeptanzkriterien.
- A fixture-driven public audit returns a schema-valid canonical measurement envelope.
- Private/loopback/link-local/metadata endpoints and DNS-rebinding cases are rejected.
- CSP, HTTP, TLS, redirect, robots, sitemap, and selected public signals can be normalized without provider-specific fields in the customer model.
- Existing 48 score metrics and the 96-field ElevenLabs v1.3 contract remain byte-/schema-compatible unless an explicitly approved migration exists.
- A customer PDF never shows an empty roadmap phase and does not expose adapter/provider jargon.
- Full regression, release, provenance, and installability gates pass on one frozen digest.

Explizit out-of-scope.
- Installing analytics or monitoring on a customer site without a separate agreement.
- Penetration testing, legal compliance certification, or a universal AI rank.
- Replacing the existing Pixelkiez PDF/visualization/CSV architecture.
- Deploying every inspected repository as a dependency.
- Write-capable MCP tools or arbitrary URL-fetch/shell tools.

Done-Definition. Gateway contracts, first public-probe slice, security tests, normalization, Pixelkiez adapter, fixtures, documentation, source map, license ledger, regression reports, and release evidence pass; the complete updated skill is packaged as `skill.zip` only after the protected baseline and all gates remain green.

Reference-Doc: `docs/plans/2026-08-30-pixelkiez-measurement-platform-integration.md`
<!-- GOAL_END -->

## Evidence and source boundary
### Provided evidence
- Uploaded repository packages for Open-Web-Analytics, Statping, CSP Auditor, and Web-Check.
- Existing Pixelkiez Website Diagnosis package and prior v3.3 presentation/SEO plan.
- Current-session repository and MCP registry metadata.

### Not yet sufficient for hard adoption
- File-level license compatibility and attribution obligations.
- Production runtime performance and security behavior.
- Customer data-processing and retention decisions.
- Live credentials for analytics/search/AI providers.

## Assumptions, missing information, open questions, blockers
### ASSUMPTION
- A VPS or container runtime can host a separate gateway.
- The first release is read-only and public-data-only.

### MISSING
- Canonical gateway repository name and deployment target.
- Final data-retention and tenancy policy.
- Choice between REST-only and REST + MCP for the first release.

### BLOCKER
- No third-party source code may be copied before license review.
- No live URL-scanning service may be deployed before SSRF and egress tests pass.

## Requirements
| ID | Type | Statement | Source | Verification |
|---|---|---|---|---|
| REQ-A-001 | Architecture | Skill and measurement runtime remain separate | Analysis | File tree and dependency check |
| REQ-A-002 | Architecture | All adapters emit one versioned envelope | Analysis | JSON Schema tests |
| REQ-F-001 | Functional | Public probe covers approved HTTP/TLS/CSP/robots/sitemap signals | User goal + repo analysis | Fixture and live-safe smoke tests |
| REQ-F-002 | Functional | Owner analytics and monitoring are optional adapters | Analysis | Missing-credential tests |
| REQ-S-001 | Security | Reject private and unsafe network targets | Security gate | SSRF test suite |
| REQ-S-002 | Security | No secrets or raw customer payloads in reports | Enterprise policy | secret/log scan |
| REQ-D-001 | Data | Provider data includes provenance, scope, conditions, time, and limitations | Evidence policy | schema validation |
| REQ-D-002 | Data | Unavailable data are not scored as failure | User value | regression test |
| REQ-NF-001 | Non-functional | Adapter failure degrades partially, not by corrupting the whole report | Architecture | failure injection tests |
| REQ-NF-002 | Non-functional | Customer projection remains concise and advisory | User feedback | rendered PDF review |
| REQ-O-001 | Operations | Timeouts, retry budgets, rate limits, caching, and cancellation are observable | Architecture | integration tests and logs |
| REQ-O-002 | Operations | Same frozen digest authorizes validation and packaging | Enterprise policy | pipeline ledger validator |

## Architecture and file boundaries
### Target repositories
1. `pixelkiez-measurement-gateway` — networked execution, adapters, raw evidence, normalized measurement envelopes.
2. `pixelkiez-website-diagnosis` — orchestration, canonical analysis merge, business interpretation, presentation, CSV/voice handoff.

### Gateway modules
```text
src/
  domain/measurement-envelope.*
  security/target-policy.*
  security/dns-rebinding-guard.*
  orchestration/run-audit.*
  adapters/public-web/*
  adapters/csp/*
  adapters/performance/*
  adapters/monitoring/*
  adapters/analytics/*
  transport/http/*
  transport/mcp/*        # optional, not first-slice requirement
  observability/*
tests/
  fixtures/
  security/
  contract/
```

### Pixelkiez skill integration
```text
schemas/measurement-envelope.schema.json
scripts/measurement_gateway_client.py
scripts/normalize_gateway_measurements.py
scripts/validate_measurement_envelope.py
references/measurement-gateway-contract.md
references/third-party-capability-source-map.md
reports/core-functionality-preservation.json
```

### Prohibited changes
- No rewrite of the canonical score engine.
- No removal or renaming of v1.3 CSV fields.
- No replacement of the existing PDF renderer or business-first story layer.
- No raw provider output in customer-facing artifacts.

## Implementation phases
### Phase 0 — Baseline and license freeze
- Snapshot newest installed skill.
- Mark parallel patches as protected.
- Inventory exact repository revisions and licenses.
- Create file-level reuse/notice ledger.

### Phase 1 — Canonical contract and security shell
- Define measurement-envelope JSON Schema.
- Implement target parsing, DNS/IP classification, redirect revalidation, limits, and cancellation.
- Add SSRF, rebinding, response-size, timeout, and redirect-loop tests.

### Phase 2 — First public-probe slice
- Implement HTTP status and redirect chain.
- Implement TLS/HTTPS observations.
- Implement robots/sitemap and selected headers.
- Implement CSP header normalization and rule findings.
- Add deterministic fixtures and error cases.

### Phase 3 — Pixelkiez adapter
- Add gateway client and envelope validator.
- Merge observations into existing non-scoring enrichment.
- Preserve existing score, business lever, presentation, PDF, CSV, and voice behavior.

### Phase 4 — Customer advisory projection
- Add only decision-relevant findings to business interpretation.
- Route critical evidenced privacy/security/contact issues to `NOW`.
- Keep provider details internal.
- Ensure roadmap/closing cross-page consistency.

### Phase 5 — Optional continuous monitoring
- Define provider-neutral availability contract.
- Evaluate Statping versus a smaller maintained provider at implementation time.
- Treat snapshot and uptime as separate metrics.

### Phase 6 — Optional first-party analytics
- Define read-only analytics contract.
- Evaluate OWA as an opt-in self-hosted provider.
- Add event/funnel taxonomy and historical-data boundary.

### Phase 7 — Optional MCP surface
- Add task-level read-only tools only after REST/domain behavior is stable.
- Run MCP Inspector and security/permission evaluations.

### Phase 8 — Full release
- Run protected baseline regressions.
- Run security and failure-injection suites.
- Render and visually inspect at least three industry fixtures.
- Freeze digest, run release hook, evaluator, validators, and package.

## Tasks
### TASK-001 — Freeze the installed baseline
Objective: prevent parallel-patch loss.
Requirements: REQ-A-001, REQ-O-002
Steps:
1. Read the currently installed/latest skill tree and digests.
2. Record protected files, contracts, and validators.
3. Add a baseline-preservation fixture.
4. Fail the test if any protected file disappears or incompatible schema change occurs.
Acceptance: protected CSV v1.3, PDF/story, score, renderer, and previous guardrails are preserved.
Rollback: discard the working copy and restore the frozen baseline.

### TASK-002 — Build the third-party source and license ledger
Objective: decide reference, reimplementation, or code reuse per component.
Requirements: REQ-S-002
Steps:
1. Record repository revision and license files.
2. Map each candidate source file to intended use.
3. Record required notices and distribution compatibility.
4. Block copied code with unresolved status.
Acceptance: every reused line/module has a resolved source and notice decision.
Rollback: reimplement behavior from documented contracts or remove the component.

### TASK-003 — Define the measurement envelope
Objective: create one provider-neutral data contract.
Requirements: REQ-A-002, REQ-D-001
Steps:
1. Write failing schema fixtures for valid, partial, failed, and unavailable runs.
2. Define JSON Schema and examples.
3. Add provenance and limitation requirements.
4. Validate all fixtures.
Acceptance: provider-specific payloads cannot masquerade as canonical observations.
Rollback: version the schema and retain the previous accepted version.

### TASK-004 — Implement SSRF and egress policy
Objective: make URL measurement safe by default.
Requirements: REQ-S-001
Steps:
1. Write failing tests for localhost, private IPv4/IPv6, metadata endpoints, link-local, redirects, and rebinding.
2. Implement parsing and IP classification.
3. Re-resolve and revalidate each redirect target.
4. Add port, scheme, timeout, response-size, and concurrency limits.
Acceptance: all unsafe-target tests fail closed before network I/O.
Rollback: disable live public probing and retain fixture-only mode.

### TASK-005 — Implement HTTP and redirect observations
Objective: establish the smallest public measurement slice.
Requirements: REQ-F-001, REQ-NF-001
Steps:
1. Write fixture tests for success, redirect, loop, timeout, and oversized response.
2. Implement bounded request execution.
3. Normalize status, final URL, redirect chain, and timing.
4. Map failure states without aborting unrelated adapters.
Acceptance: deterministic envelope for each fixture.
Rollback: disable the adapter independently.

### TASK-006 — Implement TLS and HTTPS observations
Objective: provide concrete transport/security evidence.
Requirements: REQ-F-001
Steps:
1. Write certificate and hostname fixtures.
2. Implement certificate metadata collection without claiming full security.
3. Separate HTTPS availability from other visible security signals.
Acceptance: HTTPS is never grouped with unrelated unknowns.
Rollback: mark TLS adapter unavailable.

### TASK-007 — Implement robots and sitemap observations
Objective: support classical and AI crawler access analysis.
Requirements: REQ-F-001
Steps:
1. Add fixtures for missing, allowed, blocked, malformed, and redirect cases.
2. Parse only bounded public resources.
3. Normalize crawler-specific directives as observations, not ranking claims.
Acceptance: blocked versus not measured remains distinct.
Rollback: retain raw fetch evidence and disable interpretation.

### TASK-008 — Migrate CSP rule coverage
Objective: add actionable CSP findings without a legacy runtime dependency.
Requirements: REQ-F-001, REQ-D-001
Steps:
1. Extract candidate rules and expected behavior from CSP Auditor.
2. Resolve license status.
3. Write tests for directives, wildcards, unsafe-inline/eval, framing, mixed content, and report endpoints.
4. Implement a maintained parser or small deterministic evaluator.
Acceptance: every CSP finding references the exact observed header and rule.
Rollback: revert to presence-only CSP observation.

### TASK-009 — Add provider-independent adapter orchestration
Objective: run adapters with isolation and partial failure.
Requirements: REQ-NF-001, REQ-O-001
Steps:
1. Write failure-injection tests.
2. Implement per-adapter timeout and cancellation.
3. Aggregate partial results without fabricating missing values.
4. Emit structured operational telemetry with `truth_authority: false`.
Acceptance: one adapter failure cannot corrupt successful observations.
Rollback: run adapters sequentially or disable unstable adapters.

### TASK-010 — Integrate the gateway into Pixelkiez
Objective: enrich the canonical analysis without a parallel metric store.
Requirements: REQ-A-001, REQ-D-002
Steps:
1. Write tests against frozen Pixelkiez fixtures.
2. Add client, schema validator, and normalizer.
3. Attach results to existing non-scoring enrichment.
4. Preserve metric IDs and report digest rules.
Acceptance: old reports render identically when no gateway result is supplied.
Rollback: remove the adapter hook; canonical analysis remains intact.

### TASK-011 — Add business relevance admission gate
Objective: prevent a broad technical dump.
Requirements: REQ-NF-002
Steps:
1. Write tests for useful and low-value signals.
2. Require business effect, evidence strength, actionability, and uniqueness.
3. Keep rejected observations internal.
Acceptance: customer output contains only decision-relevant findings.
Rollback: use existing four-lever selection with no new public-probe findings.

### TASK-012 — Preserve the advisory story and NOW semantics
Objective: integrate new findings into a consistent action path.
Requirements: REQ-NF-002
Steps:
1. Add tests for privacy/security/contact P0 actions.
2. Require `NOW`, `30_DAYS`, and `AFTER` consistency.
3. Build closing actions from the same canonical action plan.
4. Block empty rendered phases and sentence fragments.
Acceptance: roadmap and closing cannot contradict each other.
Rollback: suppress the new finding from customer projection.

### TASK-013 — Define continuous monitoring contract
Objective: add uptime later without coupling to Statping.
Requirements: REQ-F-002
Steps:
1. Define snapshot, time-series, incident, and maintenance records.
2. Add tests preventing one-shot-to-uptime conversion.
3. Evaluate runtime providers using maintenance, security, and operations criteria.
Acceptance: provider can be replaced without changing Pixelkiez report schema.
Rollback: omit monitoring module.

### TASK-014 — Define first-party analytics contract
Objective: support OWA or another provider safely.
Requirements: REQ-F-002, REQ-D-002
Steps:
1. Define users, sessions, landing pages, events, funnels, and outcome boundaries.
2. Add access and retention metadata.
3. Create fixtures for absent instrumentation and partial event coverage.
4. Evaluate OWA as an optional provider.
Acceptance: untracked history is never reconstructed or estimated as fact.
Rollback: retain GA4/GSC-only owner-data path.

### TASK-015 — Add optional read-only MCP wrapper
Objective: make stable measurements agent-consumable without exposing infrastructure.
Requirements: REQ-S-001, REQ-S-002
Steps:
1. Define task-level tools and narrow schemas.
2. Annotate all first-release tools read-only and non-destructive.
3. Add auth, tenant, pagination, rate-limit, and error contracts.
4. Run inspector and read-only evaluations.
Acceptance: no arbitrary fetch, shell, database, or credential tool exists.
Rollback: publish REST/OpenAPI only.

### TASK-016 — Run protected regressions and realistic proofs
Objective: prove old capabilities and new customer value together.
Requirements: all
Steps:
1. Run existing truth, score, v1.3, PDF, visual, semantic, and voice-handoff tests.
2. Run new security, contract, adapter, and cross-page tests.
3. Render local service, B2B, and hospitality fixtures.
4. Inspect customer pages for advisory clarity and no technical leakage.
Acceptance: protected baseline and new guardrails both pass.
Rollback: revert the gateway integration while keeping standalone gateway work.

### TASK-017 — Freeze, evaluate, and package
Objective: release only one proven snapshot.
Requirements: REQ-O-002
Steps:
1. Freeze the final artifact digest.
2. Run release hook, anti-confabulation, anti-sycophancy, bias, evaluator, and validators.
3. Confirm the same digest across reports.
4. Package complete updated skill as `skill.zip` only after PASS.
Acceptance: no blocked claim, failed validator, or digest mismatch.
Rollback: do not package; return to the last green freeze.

## Validation strategy
### Focused tests
- JSON Schema fixtures.
- SSRF/DNS-rebinding/redirect security tests.
- Per-adapter contract and failure tests.
- CSP rule fixtures.
- Missing-credential and unavailable-data tests.

### Broader regressions
- Existing Pixelkiez truth discipline.
- 48 core metrics preserved.
- ElevenLabs v1.3 96 fields preserved.
- Score and no-score behavior.
- PDF visual and semantic QA.
- Roadmap/closing consistency.
- Cross-skill voice packet compatibility.

### Manual review
- No provider jargon in client slides.
- No empty cards or roadmap phases.
- Strong but evidence-bounded language.
- New technical data improve a decision rather than merely fill a page.

## Rollback and safety
- Every adapter is independently disableable.
- Gateway failure leaves existing Pixelkiez analysis functional.
- Version measurement envelopes and retain backward-compatible readers.
- Do not migrate customer data or enable scheduled monitoring in the first slice.
- Keep all credentials outside the skill package and fixtures.

## Execution handoff
- Start with Phase 0 and TASK-001; no implementation before baseline and license freeze.
- Stop if any parallel patch is newer than the selected baseline.
- Stop if copied code lacks a resolved license status.
- Stop if SSRF tests cannot run in the target runtime.
- Expected first-slice artifacts: schema, security policy, public HTTP/TLS/robots/sitemap/CSP adapters, fixtures, Pixelkiez adapter, regression reports.

## Plausibility and truth self-check
- Goal length: below 4000 characters.
- Unsupported claims removed or labeled: yes.
- Strongest counterargument: a new service adds operational work.
- Failure-mode chain: if network and multi-runtime concerns remain inside the skill, validation becomes environment-specific, then reports become non-reproducible; mitigation is a bounded gateway with stable contracts and independent adapter tests.
- Bias risks: tool bias toward broad repositories, novelty bias toward MCP/AI, sunk-cost bias toward existing code, and sales bias toward turning missing data into negative findings.
- Final readiness: ready-for-execution-with-gates.
