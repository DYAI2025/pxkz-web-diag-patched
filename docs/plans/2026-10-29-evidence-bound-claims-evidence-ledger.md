# Evidence-bound customer claims — evidence ledger

Branch feature/pixelkiez-packaged-brand-fonts, base 6db8fb1. Every row: command, exit code, value, pasted from terminal.
Runtime: `~/.venvs/pxkz-ebc` (uv, CPython 3.12, `requirements.txt` + pytest), `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`; WeasyPrint 68.1.

## Task 1 — baseline (2026-10-29)
| check | command | rc | value |
|---|---|---|---|
| worktree clean | `git status --porcelain \| wc -l` | 0 | 0 |
| HEAD | `git rev-parse --short HEAD` | 0 | 6db8fb1 |
| tree digest | `python3 -B scripts/pipeline_ledger.py digest .` | 0 | bc58cd9a6c9061258020974b9e11f8b17b89de61c5440a78efdd48b8752e941d |
| release gate (system python) | `python3 -B scripts/validate_release_gate.py .` | 1 | FAIL; includes FONT_UNREADABLE_OR_FONTTOOLS_UNAVAILABLE (system python lacks fontTools) |
| release gate (venv) | `$PY -B scripts/validate_release_gate.py .` | 1 | FAIL: release status not PASS; semantic gate not PASS (no font error) |
| full suite (venv) | `$PY -B -m pytest tests -q` | 0 | 186 passed, 69 subtests passed |
| defect lines | rg fingerprints | 0 | client_story.py:20-22,28-30,36,60; build_visualization_plan.py:230; build_client_report_model.py:186; finalize_deliverable_manifest.py:91 |

## Task 2 — red suite
| check | command | rc | value |
|---|---|---|---|
| red suite | `$PY -B -m unittest tests.test_evidence_bound_claims -v` | 1 | Ran 14; failures=10 errors=3 (KeyError evidence_method/metric_ref/context_label); Case7 canary ok |

Deviations from plan: `clientize(text, limit)` has a required limit → tests pass 200. PDF byte change is already caught by receipt digest, so Case 8 targets the real gaps: READY without PASS QA, tampered required artifact not in receipt. Strength rule tightened to `customer_status == CLEAR` (a `minor_gaps` metric is shown as "Verbesserung sinnvoll" in V10; a strength on it would contradict the visual).

## Task 3 — meaning-preserving simplification
| check | command | rc | value |
|---|---|---|---|
| golden pairs + case 1 + case 2 text | `$PY -B -m unittest tests.test_evidence_bound_claims.GoldenPairs …Case1LabStaysLab …test_synthetic_wording_is_not_called_documented` | 0 | Ran 5, OK |
| guardrails on synthetic client model | `$PY -B scripts/validate_customer_output_guardrails.py <model>` | 0 | PASS artifacts=1 |
| existing suites | `$PY -B -m pytest tests -k 'not Case and not GoldenPairs'` | 1 | 186 passed; 2 expected legacy-oracle drifts: synthetic-report plan, model (amended in Task 6) |
| method classifier spot check | `evidence_method(...)` | 0 | Lighthouse+field-limitation→LAB, CrUX→FIELD, Synthetic→SYNTHETIC, mode FIELD→FIELD |

Deviation: no sentence-capitalisation pass (would change unrelated outputs); sentence-initial case kept by `_keep_case` callables instead. Compound rule `Lighthouse/PageSpeed-Labortest` moved before the generic `Labortest` rule so it can fire. Golden pair for `Kernsample` dropped: the existing rule yields ungrammatical "Das geprüften Seiten" and is not a method/scope rule.

## Task 4 — claims bound to scored metrics
| check | command | rc | value |
|---|---|---|---|
| cases 3, 5 (+ validator negative) | `$PY -B -m unittest …Case3SampleScopeStaysVisible …Case5NoOppositeStrength` | 0 | Ran 3, OK |
| full suite | `$PY -B -m pytest tests -q` | 1 | 195 passed; 9 failed = 7 Task-5/6 targets + 2 known oracle drifts (synthetic-report plan, model); legacy lever_ids unchanged |

Rule as implemented: a strength is admitted only from a positive finding whose every metric_ref is assessed, reads "Klar" under `customer_status` and is not contested by a legal/identity risk; AI-06-only claims get whole-site wording rewritten to "auf den geprüften Seiten", other whole-site wording is refused. Free-text `top_strengths` are recorded as `NO_FINDING_LINK`. Levers on the core-metric route whose every linked assessed metric reads "Klar" are not selectable. Critical and MANDATORY_CRITICAL levers go to roadmap "now". Sidecar `customer-claim-bindings.json` is a required bundle artifact, validated in the build and in `validate_deliverable_bundle.py`.

## Task 5 — visuals, one status scale, synthetic block
| check | command | rc | value |
|---|---|---|---|
| full suite | `$PY -B -m pytest tests -q` | 1 | 200 passed; 5 failed = 3 Case8 (Task 6) + 2 known oracle drifts |
| visual architecture eval (scratch copy) | `$PY -B scripts/run_visual_architecture_evals.py .` | 0 | PASS |
| template gallery eval | `… run_visual_template_gallery_evals.py .` | 0 | PASS |
| customer semantic eval | `… run_customer_semantic_evals.py .` | 0 | PASS |
| legal customer projection eval | `… run_legal_customer_projection_evals.py .` | 0 | PASS |
| presentation quality eval | `… run_customer_presentation_quality_evals.py .` | 0 | PASS |
| business-first eval | `… run_business_first_reporting_evals.py .` | 0 | PASS |
| VC03 customer release eval | `… run_vc03_customer_release_evals.py .` | 0 | PASS |
| chart template eval | `… run_chart_template_evals.py .` | 1 | ModuleNotFoundError reportlab (legacy renderer, not in requirements.txt; environmental) |

Decisions measured during the task:
- The active-core path (synthetic report + `full-48-core-execution.json`, bundle `mode: FIXTURE`) is fixture data too: materialized metrics carry `note: FIXTURE_ONLY_NOT_LIVE_EVIDENCE` and `value.fixture: true`. `evidence_method` treats those structural markers as SYNTHETIC. Result: no repository fixture can produce a customer-mode PDF; customer mode refuses with `CUSTOMER_RELEASE_BLOCKED: SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT` (checked per selected visual and per metric behind it). Proof mode keeps fixture outputs, labelled "Beispieldaten, keine Live-Messung".
- `tests/test_positive_customer_e2e.py` and `tests/test_packaged_brand_fonts.py::OfflineStrictRenderTests` now build `--release-mode proof --require-exact-fonts` (same strict font contract); the positive E2E additionally asserts the customer-mode refusal.
- Matrix values: V08 Vega tints by value on 0/0.5/1, V10 by label. Shared anchor `MATRIX_VALUE` (Klar 1.0, Verbesserung sinnvoll 0.5, Handlungsbedarf 0.0) gives the same colour for the same status in both renderers; V08 still omits unscored rows (no neutral colour on its scale).
- `schemas/visualization-plan.schema.json` gains optional `evidence_method` (LAB/FIELD/SYNTHETIC); the schema is not in the protected baseline.

## Task 6 — fail-closed validators, live eval, override evidence
| check | command | rc | value |
|---|---|---|---|
| Case 8 (3 tests) | `$PY -B -m unittest tests.test_evidence_bound_claims.Case8ReadyIsInvalidated` | 0 | OK |
| mutation canary | `$PY -B -m unittest tests.test_evidence_bound_claims.MutationCanary` | 0 | lab→device mutation makes the inner eval FAIL (Case1 + GoldenPairs fail) |
| claim eval, venv | `$PY -B scripts/run_evidence_bound_claim_evals.py .` | 0 | PASS ran=17 skipped=0 |
| claim eval, system python (skip canary) | `python3 -B scripts/run_evidence_bound_claim_evals.py . --json-out …` | 1 | FAIL skipped=4 (PDF runtime missing → NOT RUN) |
| protected baseline | `python3 -B scripts/validate_measurement_platform_baseline.py .` | 0 | PASS exact=35 overrides=12 chained=7 reports=12 (was rc 1 invalid_override ×5 before the override report) |
| legacy oracles | `$PY -B -m unittest tests.test_legacy_oracles` | 0 | OK after amendment (synthetic-report plan 894ea740…→45a14b49…, model a881d84f…→77793c00…; lever ids unchanged) |
| quick_validate (named copy) | `python3 -B <copy>/scripts/quick_validate.py <copy>` | 0 | PASS 317 required files |
| full suite | `$PY -B -m pytest tests -q` | 0 | 204 passed, 69 subtests |

Implementation notes: finalize downgrades a stored READY to BUILT_PENDING_QA before revalidation and writes CUSTOMER_RELEASE_BLOCKED with block_reason on any failure (atomic replace). Bundle validation checks every `required_artifacts[].sha256` and refuses READY without PASS visual+semantic QA bound to the receipt PDF digest. Release gate loads `reports/evidence-bound-claims-eval-results.json` (PASS, no skips, digest = live tree) and re-runs the suite live.

## Task 7 — part 1: fresh nine-case build found two defects (fixed TDD before review)
| check | command | rc | value |
|---|---|---|---|
| first nine-case build | `$PY -B scripts/run_customer_release_cases.py <named copy> <out>` | 1 | proof-strategic FAIL `SVG font too small VIZ-006=9.0px` (V05 per-row caption from Task 4) |
| red: SVG legibility | `…Case6RankingContextPerRow.test_per_row_context_stays_legible_in_the_rendered_svg` | 1 | `9.0 not greater than or equal to 13` |
| green after fix | same | 0 | caption 13 px, row pitch 34, 8 rows end y=387 < footer 407 |
| red: example-data notice | `…Case2SyntheticStaysSynthetic` (model + every proof page) | 1 | pages [1,2,3,4,6,7,8,9,10] without "Beispieldaten"; model meta has no notice |
| red: real-data template path | `…test_real_data_template_keeps_its_sampling_basis` | 1 | `UndefinedError: 'dict object' has no attribute 'sample_data_notice'` (StrictUndefined) |
| green | `$PY -B -m pytest tests/test_evidence_bound_claims.py tests/test_positive_customer_e2e.py` | 0 | 28 passed |
| legacy oracles | `$PY -B -m unittest tests.test_legacy_oracles` | 0 | amendment updated in place: synthetic-report model 77793c00…→e5f745cc… (plan unchanged) |
| protected baseline | `python3 -B scripts/validate_measurement_platform_baseline.py .` | 0 | PASS; override scope now 6 files incl. templates/presentation.html.j2 |
| v3.2.1 layer | `add_v321_patch_layer.py` + validator | 0 | 23 transitions; PASS modified=73 added=85 |
| full suite | `$PY -B -m pytest tests -q` | 0 | 209 passed, 69 subtests |
| claim eval | `$PY -B scripts/run_evidence_bound_claim_evals.py .` | 0 | PASS ran=22 skipped=0 |

Deviation: case B (synthetic priority profile) builds without `--require-exact-fonts`, because build_audit_deliverables refuses that pairing by design; its receipt still has to read EXACT/VERIFIED or the builder fails. All five former customer cases are first attempted in customer mode and must be refused (`SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT`, no PDF); the nine inspectable PDFs are proof-mode builds of fixture data, now labelled "Beispieldaten" on every page. They are not nine live audits.

## Task 7 — part 2: fixture-replay rankings (found by own raster check of the frozen 4671d0a build)
proof-strategic page 8 showed SERP rankings from an offline `mode: FIXTURE` bundle (`source_type: FIXTURE_REPLAY`) dated with the replay time (29.10.2026) and without evidence_method, so the customer-mode block could not see them.
| check | command | rc | value |
|---|---|---|---|
| red | `…Case6RankingContextPerRow.test_fixture_replay_rankings_are_example_data_without_a_measurement_date` | 1 | `None != 'SYNTHETIC'` |
| red | `…Case6RankingContextPerRow.test_example_data_enrichment_blocks_customer_mode` | 1 | `'MEASUREMENT_ENRICHMENT' not found` |
| green | `$PY -B -m unittest tests.test_evidence_bound_claims.Case6RankingContextPerRow` | 0 | 4 tests OK |
| full suite | `$PY -B -m pytest tests -q` | 0 | 211 passed, 69 subtests |
| evals | enrichment / gateway / strategic / visual architecture / customer semantic / VC03 / branch priority / legal projection | 0 | all PASS (gateway after override refresh) |
| baseline + v3.2.1 | validators | 0 | PASS / PASS (23 transitions) |
