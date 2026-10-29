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

## Task 7 — review round 1 (independent adversarial reviewer, 39/39 unique rasters of 6846366 opened)
Result: 11 confirmed, 4 plausible findings, so QA was NOT signed. Each was re-derived from files before acting.
| finding | verdict after re-derivation | action |
|---|---|---|
| F1 blocker: closing highlights "Reale Nutzung … 2026-08-01 bis 2026-08-28", "Reale Ladeerfahrung … dokumentierter Zeitraum" from `FIXTURE_REPLAY` | confirmed (PDF text + model) | fixed: example data → "Nutzung"/"Ladeerfahrung", context "Beispieldaten"; LCP named "Hauptinhalt sichtbar nach … (p75)" |
| F2/F3 roadmap "Jetzt" vs next step/closing order; P1/P2 re-derived from severity | confirmed (source roadmap F-003 now, F-002 P1, F-004 P2) | fixed: audit roadmap entry (evidence_basis) decides slot + priority; next step and closing follow that order |
| F4 active-positive lever F-001 vs UX-02 = 100 "Klarheit des nächsten Schritts" | confirmed (fixture stitches legacy findings onto full-48 FIXTURE metrics) | OPEN — owner decision (lever admission rule or consistent positive fixture) |
| F5 V08 AI-05 = 100 shown "Verbesserung sinnvoll" via non-lever F-005 | confirmed | fixed: cap only from the four levers; test_legal_trust_boundary aligned to its "customer-visible" docstring + hidden-finding control |
| F6 V02 trust bar 89 under legal risk | confirmed | fixed: bar withheld while legal projection contests its metrics (recorded in V02 population) |
| F7 V07 page for non-lever F-002 | confirmed as observation; chart is evidence-bound | OPEN — owner decision (visual admission policy) |
| F8 #566360 on orange 1.87:1 | confirmed | fixed: ink on orange pages |
| F9 empty "Stärken" column | confirmed | fixed: column omitted when empty |
| F10 "3.8" without unit; "Ladezeit" for LCP | confirmed | fixed: "3,8 s", "Ziel ≤ 2,5 s", subtitle "Mobile Anzeige des Hauptinhalts" |
| F11 ranking axis unnamed | confirmed | fixed: "Position N" / "Position 1" scale labels |
| P1 page-2 footer date next to "Beispieldaten" | plausible → fixed | footer "Auf einen Blick" for example data |
| P2 "KI-Antworten wurden nicht abgefragt." | not a defect | intentional scope boundary from the claim-scope patch |
| P3 `font_resolution.customer_release_ready` | not a defect | font sub-status; top-level status stays BUILT_PENDING_QA |
| P4 "die Website läuft über HTTPS" | not a defect | site-level transport property, not a sample claim |
| reviewer note: customer mode not attempted for 4 cases | confirmed | builder now attempts customer mode for all nine |

| check | command | rc | value |
|---|---|---|---|
| red | `…ReviewRoundOne` (9 tests) | 1 | 9 failures, each for the stated reason |
| green | `$PY -B -m unittest tests.test_evidence_bound_claims` | 0 | 33 tests OK |
| full suite | `$PY -B -m pytest tests -q` | 0 | 220 passed, 69 subtests |
| 12 eval suites | enrichment, gateway, strategic, visual architecture, customer semantic, VC03, branch priority, legal projection, business-first, gallery, truth discipline, reporting bundle | 0 | all PASS |
| oracles | amendment in place: plan 45a14b49…→ac5e2787…, model e5f745cc…→ffae93dd…; lever ids unchanged | 0 | OK |
| baseline / v3.2.1 | validators | 0 | PASS (7 override files incl. assets/presentation.css) / PASS 25 transitions |

### Task 7 — own look at the frozen build of 3a1f4da (before dispatching reviewer round 2)
Frozen build from `git archive 3a1f4da`: rc 0, 9 cases, 90 pages / 41 unique rasters, crosscheck BAD 0; customer mode refused for all nine cases (8 × `SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT`, case B × synthetic priority profile) plus both negatives, no PDF written.
Inspected pages: proof-strategic 08 (V05 scale), 10 (roadmap), 11 (highlights); legacy-baseline 05 (V07), 08 (orange lever page); legal-golden 02. The fixes look as intended. One new defect: with the strengths column hidden, the priorities column stayed half-width (right half of the card empty).
| check | rc | value |
|---|---|---|
| red `test_empty_strengths_leave_no_empty_column` (+ `summary-columns single`) | 1 | assertion failed for the stated reason |
| green after template class + `.summary-columns.single` CSS | 0 | OK |
| full suite | 0 | see commit; claim eval PASS ran=33 skipped=0 |

## Task 7 — review round 2 (fresh independent reviewer, 41/41 unique rasters of 9c506de opened)
Result: 18 findings (1 blocker, 9 major), so QA was NOT signed. Each fix-candidate was re-derived from code/data before acting.
| finding | verdict after re-derivation | action |
|---|---|---|
| R01/R02 active-positive lever F-001 vs UX-02 = 100; findings and metrics from different snapshots | confirmed (= round-1 F4) | OPEN — owner decision (fixture vs lever rule) |
| R03 lever order (business rank) ≠ execution order (audit roadmap); HOCH under "Danach" | confirmed | OPEN — owner decision (one order, or explain both) |
| R04 MANDATORY_CRITICAL legal lever shown "01 · HOCH" | confirmed (template maps severity only) | fixed: model shows it as critical |
| R05 legal-override rows "Handlungsbedarf" next to TRUST-01 = 100 and score 65 incl. trust 89 | confirmed | OPEN — owner decision (legal projection semantics) |
| R06 presence-only TRUST-01/02 shown "Klar" for rechtliche Angaben/Datenschutz | confirmed (registry score_mode presence_only) | OPEN — owner decision (presence wording vs status) |
| R07 "HTTPS & sichtbare Sicherheitsangaben · Klar" with 0 security headers | confirmed | fixed: row named "HTTPS-Verschlüsselung" |
| R08 "Testmessung" vs spec "Laborwerte bleiben als Labor bezeichnet" | spec ↔ guardrail conflict; plan chose "Testmessung" | OPEN — owner confirmation |
| R09 field LCP 3,2 s and lab 3,8 s both unmarked | confirmed | fixed: field value reads "bei 3 von 4 Besuchen" |
| R10/R11 V07 page and case-c lever selection vs audit roadmap | confirmed (= round-1 F7) | OPEN — owner decision (visual admission) |
| R12 LCP action asserts images as cause, drops re-measure | confirmed (client_story replacement) | fixed |
| R13 case-a cover without warning while two levers are KRITISCH | confirmed | OPEN — minor, part of R03 decision |
| R14 "gut macht"/"Was heute trägt" titles with no strengths | confirmed | fixed |
| R15 footer/subtitle 3.57:1 on sage | confirmed | fixed: #3A4543 |
| R16 V05 position 1 plotted at x=784, label at 810 | confirmed | fixed: axis ends match labels |
| R17 legacy ≡ gateway, legal-golden ≡ proof-realistic (identical PDFs) | confirmed | OPEN — case design; counted as 41 unique rasters, not nine proofs |
| R18 plausible minors (p75 jargon fixed with R09; rest noted) | partly | p75 fixed; others open |

| check | rc | value |
|---|---|---|
| red `ReviewRoundTwo` (7 new tests) | 1 | 7 failures, each for the stated reason |
| green claim suite | 0 | 49 tests OK |
| full suite | 0 | 236 passed, 69 subtests |
| 12 eval suites | 0 | all PASS |
| oracles | 0 | amendment in place: plan ac5e2787…→8f23ac34…, model ffae93dd…→4146f0fb…; lever ids unchanged |
| baseline / v3.2.1 | 0 | PASS / PASS 25 transitions |

### Task 7 — owner decisions on review round 2 (asked and answered 2026-10-29)
| question | decision | implementation |
|---|---|---|
| R03 lever order vs execution order | keep both, label them | V03 "Nach geschäftlicher Bedeutung geordnet; die Reihenfolge der Umsetzung zeigt der Fahrplan"; lever page "Nach geschäftlicher Bedeutung geordnet …"; closing "REIHENFOLGE DER UMSETZUNG"; audit roadmap timing stays authoritative |
| R05/R06 legal and presence rows | presence wording | present presence-only rows (TRUST-01/02) read "… (vorhanden) · Nicht belastbar bewertet"; rows contested by a projected legal/identity risk read "Nicht belastbar bewertet" in V10 and stay out of the value-tinted V08; scores untouched |
| R08 lab term | keep "Testmessung" | recorded as the customer-safe lab designation; guardrail unchanged |
| F4/R01/R02, F7/R10/R11, R17 fixtures | all four measures | lever rejected when its primary cited metric reads "Klar"; V07 only for one of the four levers; active-positive built from `evals/fixtures/active-positive-consistent-findings.v1.json` (findings cite weak metrics, positives cite strong ones, evidence ids from the full-48 execution); proof-realistic = legal projection + enrichment; gateway case asserts PDF == legacy-baseline (non-scoring layer without customer surface), any other identical pair fails the run |
| R13 case-a cover without warning | builder defect, not design | case-a and case-c inputs are re-scored after mutation, so blocker_present matches the findings |

Consequence recorded: the bare branch-priority tie report under its synthetic profile now has 3 visuals (F-002 is no lever, so no V07) and fails closed with CUSTOMER_MIN_VISUALS_NOT_MET — pinned by `test_bare_tie_report_under_profile_fails_closed`; case B and the plan/model agreement test carry the offline search/visitor enrichment.

| check | rc | value |
|---|---|---|
| red `ReviewRoundThree` | 1 | 5 failures for the stated reasons (R13 and fixture consistency passed on scored input → builder defect) |
| green claim suite | 0 | OK |
| canary legal eval vs cd8689d plan builder | 1 | FAIL legal row check (live) |
| canary identity check (identity cap reverted) | 1 | FAIL "identity rows not marked as not assessed …" (live) |
| full suite | 0 | see commit message |
| 12 eval suites | 0 | all PASS (legal projection eval updated to the decision, rows matched by metric_ref) |
| synthetic-report plan diff vs cd8689d | — | only V03 subtitle and TRUST-01/02 rows changed; lever ids unchanged |
| oracles / baseline / v3.2.1 / quick_validate | 0 | amendment in place (plan 8f23ac34…→ac9dc88e…) / PASS / PASS / PASS 319 files |
