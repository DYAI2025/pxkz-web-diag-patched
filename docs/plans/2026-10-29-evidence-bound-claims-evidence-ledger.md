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
