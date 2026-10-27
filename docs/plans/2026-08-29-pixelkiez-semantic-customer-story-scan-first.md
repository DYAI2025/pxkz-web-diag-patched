# Pixelkiez Scan-First Semantic Customer Story Implementation Plan

Plan path: `docs/plans/2026-08-29-pixelkiez-semantic-customer-story-scan-first.md`
Status: ready-for-execution
Owner/Executor: coding agent + semantic/visual reviewer
Last updated: 2026-08-29

<!-- GOAL_START -->
Goal: Scan-first Kundenstory vor dem PDF-Rendern erzwingen

Ziel. Der Website-Diagnosis-Skill soll bereits bei Auswahl, Verdichtung und Formatwahl der Kundeninhalte eine kurze, konkrete und verständliche Geschichte erzeugen. Website-Probleme werden in natürlicher Alltagssprache erklärt; direkt messbare oder zählbare Signale werden bevorzugt als Zahl oder Visual statt als Fließtext dargestellt. Die finale semantische PDF-QA bleibt als fail-closed Sicherheitsnetz bestehen, soll aber nicht die primäre Redaktionsschicht sein.

Scope. Änderungen betreffen Kundenstory-Policy, Client-Report-Modell, deterministische Formatwahl pro Finding, quantitative Signalextraktion, Finding-Rendering, semantische Modellvalidierung, rendered-PDF-Semantik-QA, Evals, Release-Gate, Provenienz und Packaging. Der kanonische Audit, Scoring, v1.3-CSV-Vertrag und Voice-Handoff bleiben fachlich unverändert.

Bedingungen (hart).
- Probleme kurz, konkret und ohne Fachjargon formulieren; keine generischen Optimierungsfloskeln.
- Direkt gemessene/beobachtete Zahlen nicht in erklärendem Fließtext verstecken, wenn eine klare Zahlendarstellung möglich ist.
- Zahlen nur aus kanonischer `measured`/`observed` Evidenz; keine erfundenen Schwellen, Benchmarks oder Wirkungsschätzungen.
- Beispiele dienen als Positiv-/Negativmuster, niemals als kundenspezifisch wiederzuverwendende Textschablone.
- Eine finale PDF darf nur nach struktureller, visueller und semantischer Kunden-QA als vollständig gelten.

Akzeptanzkriterien.
- Jedes priorisierte Finding erhält deterministisch `NUMBER_FIRST`, `EVIDENCE_VISUAL` oder `SHORT_TEXT`.
- Direkt quantitative Findings erhalten ein evidenzgebundenes `numeric_signal`; qualitative Findings bleiben kurze Klartextprobleme.
- Generische Aussagen wie „Hier besteht Optimierungspotenzial“ lassen die semantische Modellvalidierung fehlschlagen.
- Das PDF rendert vorhandene `numeric_signal` sichtbar und scanbar.
- Eine digest-gebundene Semantic-Customer-QA prüft Customer Specificity, Scanbarkeit, Verständlichkeit, Evidence Fidelity, Priorisierung, Visual-Semantik und Cross-Page-Coherence.
- Semantik-Evals, bestehende PDF-/Marketing-/Score-/Truth-/v1.3-Regressions und Release-Gates bestehen gemeinsam.

Explizit out-of-scope.
- Neue Auditmetriken oder externe Benchmarks.
- Änderung der 96 v1.3 CSV-Felder oder Voice-Agent-Contract-Semantik.
- Behauptung eines Conversion-, Umsatz- oder Rankingeffekts ohne Outcome-Evidenz.
- Vollautomatische natürliche Sprachbewertung ohne Vision-/Human-Review als Ersatz für die finale semantische QA.

Done-Definition. Der installierte Skill erzeugt scan-first Client-Modelle, besteht die neue semantische Regression, rendert quantitative Signale sichtbar, erzwingt eine echte finale Semantic-Customer-QA und wird erst nach vollständiger Regression, neuem Freeze, Release-Hook, Evaluator, Ledger und Packaging installiert.

Reference-Doc: `references/semantic-customer-story-policy.md`
<!-- GOAL_END -->

## Evidence and source boundary
- User requirement: Kunden überfliegen die Präsentation; Probleme müssen kurz/natürlich sein, Zahlen/Charts sollen quantitative Inhalte tragen.
- Existing skill evidence: `client_story.py`, `build_client_report_model.py`, `client-storytelling-contract.md`, `validate_client_semantics.py`, visual-QA scripts and PDF renderer.
- No external capability or web research is required.
- `SOURCE_NEEDED`: commercial outcome claims remain unsupported and prohibited.

## Requirements
| ID | Type | Requirement | Verification |
|---|---|---|---|
| REQ-F-101 | Functional | Per Finding deterministic presentation mode | semantic eval |
| REQ-F-102 | Functional | Direct numeric evidence becomes numeric_signal | semantic eval |
| REQ-F-103 | Functional | Generic customer copy fails | negative mutation |
| REQ-F-104 | Functional | Number-first signal rendered in PDF | PDF text/render check |
| REQ-F-105 | Functional | Final semantic QA manifest required for completed PDF | manifest validator |
| REQ-NF-101 | Non-functional | No invented numbers/thresholds | evidence-class/source checks |
| REQ-NF-102 | Non-functional | Findings remain short and scanable | deterministic length/structure checks |
| REQ-A-101 | Architecture | Semantic generation precedes QA; QA does not rewrite content | code boundary review |
| REQ-A-102 | Architecture | v1.3 batch/voice interfaces unchanged | existing regressions |

## Architecture and file boundaries
1. `references/semantic-customer-story-policy.md`: semantic control policy and examples.
2. `scripts/customer_story_semantics.py`: deterministic signal extraction, mode choice and semantic checks.
3. `scripts/build_client_report_model.py`: emit semantic finding metadata and story summary.
4. `scripts/render_diagnosis_pdf.py`: render quantitative signal as a scan-first visual element.
5. `scripts/validate_client_semantics.py`: fail on generic/verbose/non-scanable model output.
6. `scripts/create_customer_semantic_qa_manifest.py` + `validate_customer_semantic_qa.py`: final digest-bound semantic inspection contract.
7. Existing visual QA remains separate; semantic QA is additive.

## Implementation phases
### Phase 0 — RED baseline
Add semantic evals that fail because presentation modes, numeric signals and generic-copy rejection are absent.

### Phase 1 — Proactive semantic composition
Implement deterministic `NUMBER_FIRST`, `EVIDENCE_VISUAL`, `SHORT_TEXT`; extract direct numeric signals; add skill instructions and example patterns.

### Phase 2 — Scan-first model and renderer
Extend client schema/model and render numeric signal prominently without adding page count or narrative density.

### Phase 3 — Final semantic customer QA
Add digest-bound semantic QA manifest with actual vision/human inspection requirements. No self-certification.

### Phase 4 — Regression and release
Run semantic, fixture, marketing, charts, score, truth, v1.3, paired-release and core parity checks; update release reports only after code freeze.

### Phase 5 — Provenance, package, install
Create new `DRAFT_FROZEN`, evaluator/validation/package events on exact digest; package as `skill.zip`; replace installed Website Diagnosis directory with validated package content and re-run install smoke checks.

## Rollback and safety
- Source package `/mnt/data/pixelkiez_v13_release/website/skill.zip` remains rollback baseline.
- Do not alter v1.3 contract bytes.
- Do not weaken existing visual/Truth/CSV gates to make semantic tests pass.
- Semantic QA never authorizes legal, provider or live-call behavior.

## Plausibility and truth self-check
- Smallest robust slice: yes; extends existing story/model/QA pipeline rather than replacing it.
- Strongest counterargument: free-form LLM rewriting could sound more natural, but would be less reproducible and could invent meaning. Use policy-guided source authoring plus deterministic projection and final semantic review instead.
- Failure-mode chain: generic input -> generic PDF -> formal QA passes -> customer sees vague agency language. Mitigation: pre-render semantic mode/specificity gate + rendered semantic review.
- Final readiness: ready-for-execution.
