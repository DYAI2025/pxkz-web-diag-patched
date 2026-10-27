# Pixelkiez Truth-Discipline + v1.3 Cross-Skill Fix Implementation Plan

Status: implemented pending final release/provenance validation  
Owner/Executor: coding agent + reviewer  
Last updated: 2026-08-29

<!-- GOAL_START -->
Goal: Pixelkiez Audit-to-Voice Pipeline fail-closed reparieren

Ziel. Die Pipeline Website Diagnosis -> Audit Packet -> ElevenLabs Batch -> Voice Architect -> Release verhindert jede Hochstufung von Hypothesen zu `VERIFIED_FACT`, verwendet den v1.3-Vertrag mit denselben 96 Headern und fünf Rollen und trennt Upload-Bereitschaft von Production-Call-Bereitschaft. Producer und Consumer müssen byte-identisch auf denselben v1.3-Digest gebunden sein.

Scope. `pixelkiez-website-diagnosis` und die Contract-/Consumer-/Release-Grenzen von `pixelkiez-adaptive-elevenlabs-appointment-agent-architect`.

Bedingungen (hart).
- `VERIFIED_FACT` nur aus deterministisch zulässiger direkter Evidenz.
- v1.3 behält 96/96 v1.2-Header.
- Genau eine Rolle je Feld: `INTERNAL_RECORD`, `EL_RUNTIME_REQUIRED`, `EL_RUNTIME_DEFAULTED`, `OPTIONAL`, `PRODUCTION_GATE_ONLY`.
- `BATCH_READY_FOR_UPLOAD` und `PRODUCTION_CALL_READY` sind getrennt.
- Kein gepaarter Release-PASS bei Peer-/Digest-/Harness-Fehler.
- Provenienz erst nach finalem Non-Report-Freeze.

Akzeptanzkriterien.
- Truth-Countertest kann `inferred_risk` nicht in `VERIFIED_FACT`/`verified_finding` überführen.
- v1.3 = 96 Header und 96 Rollen.
- Upload-ready / production-blocked ist ein gültiger Zustand.
- Producer/Consumer v1.3 SHA-256 identisch.
- Peer-Failure und Digest-Drift blockieren Release.
- Truth, Contract, Consumer Harness, Pair Gate und beide Ledger sind im finalen Evidence-Epoch grün.

Explizit out-of-scope.
- Neue CSV-Spalten oder Änderung der 96 Header.
- Sales-/Persona-Neudesign außerhalb nötiger Evidence-Sicherheit.
- Behauptung rechtlicher Call-Freigabe oder realen Provider-Erfolgs aus lokalen Tests.
- Abschaffung v1/v1.1/v1.2.
- Allgemeine Neuarchitektur beider Skills.

Done-Definition. Beide Skills sind auf demselben v1.3-Digest, alle Gegen-/Contract-/Harness-/Release-/Ledger-Prüfungen bestehen gegen die tatsächlich installierten Skill-Verzeichnisse und erst danach wird Packaging autorisiert.

Reference-Doc: `docs/plans/2026-08-29-pixelkiez-truth-v13-cross-skill-release-fix.md`
<!-- GOAL_END -->

## Requirements

- REQ-F-001: Evidence-Class deterministisch aus kanonischem Audit ableiten.
- REQ-F-002: `verified_finding` ausschließlich aus abgeleitetem `VERIFIED_FACT`.
- REQ-F-003: Upload- und Production-Call-Gate trennen.
- REQ-D-001: v1.3 behält exakt 96 v1.2-Header.
- REQ-D-002: 96/96 Felder besitzen exakt eine der fünf Rollen.
- REQ-D-003: v1/v1.1/v1.2 bleiben explizite Kompatibilitätsmodi.
- REQ-A-001: Producer und Consumer tragen byte-identische v1.3-Contract-Dateien.
- REQ-A-002: Version/Digest/Feldanzahl in Manifest, Receipt und Release State binden.
- REQ-A-003: aktive Consumer-v1.3-Logik darf nicht auf 82/81 fest verdrahtet sein.
- REQ-A-004: tatsächliche Cross-Skill-Parität gehört zum gepaarten Releasepfad.
- REQ-NF-001: Regeln deterministisch/offline testbar.
- REQ-NF-002: kein False Green bei Peer-/Digest-Drift.
- REQ-O-001: Provenienz nach unverändertem finalem Artifact Tree.
- REQ-S-001: Sentinels/defaults werden nicht zu gesprochenen Fakten.

## Implementation order

### Phase 0 - RED baseline
1. Truth-Leak als permanente Regression erfassen.
2. Consumer-v1.3-Parität und Release-False-Green als negative Kontrollen erfassen.
3. Vorherigen Ledger-Zustand nur dokumentieren, nicht kosmetisch korrigieren.

### Phase 1 - Truth discipline
1. Zentralen `scripts/evidence_policy.py` einführen.
2. `measured`/`observed`, `inferred_risk`, `not_assessed`, mixed evidence und unresolved refs deterministisch mappen.
3. Manuelle `voice_hook.evidence_class` nur als gleich/konservativer Assertion zulassen.
4. CSV und provider-neutralen Packet Builder auf dieselbe Policy umstellen.
5. `verified_finding` nur aus `VERIFIED_FACT` befüllen; sonst nicht-faktischer Sentinel.
6. 8-case Truth-Suite ausführen.

### Phase 2 - v1.3 contract
1. 96/96 Rollenmatrix erzeugen.
2. `pixelkiez-elevenlabs-batch-contract-v1.3.json` additiv anlegen; v1/v1.1/v1.2 unverändert lassen.
3. Role-aware Contract-Utilities und v1.3 Schemas erzeugen.
4. `BATCH_READY_FOR_UPLOAD` von `PRODUCTION_CALL_READY` trennen.
5. Golden State upload-ready/production-blocked und vollständigen Production-Test hinzufügen.
6. Legacy-Regressionen weiter ausführen.

### Phase 3 - actual consumer migration
1. v1.3-Bytes unverändert in den installierten Voice Architect übernehmen.
2. Contract-/Schema-/Compiler-/Receipt-/State-/Harness-Code auf 96/95 umstellen.
3. Provider-neutrales Website-Packet rückwärtskompatibel konsumieren.
4. Consumer darf Evidence-Class nie hochstufen; `verified_finding` bleibt fail-closed.
5. Tatsächlichen installierten Consumer gegen Producer-Digest prüfen.

### Phase 4 - fail-closed release
1. Website Release Gate verlangt Voice-side PASS, v1.3 Digest/Version/96/95 und paired evidence.
2. Consumer Release Gate verlangt aktuellen Producer, v1.3 Digest und vollständigen Harness.
3. Mutationstests: voice FAIL, digest mismatch, version mismatch, count mismatch, paired FAIL, harness FAIL, Truth-E2E FAIL.
4. `validate_paired_release.py` in beide Packaging-Pfade aufnehmen.

### Phase 5 - installed E2E
1. Provider-neutralen Website-Packet erzeugen und im tatsächlichen Voice Architect kompilieren.
2. Truth-Attack (`inferred_risk`) vollständig durch Producer -> Packet -> Consumer laufen lassen.
3. Voice Harness ausführen: upload-ready/production-blocked und contract-production-ready bleiben live `NOT_AUTHORIZED`.
4. Gepaarte Release-Evidenz in beide Skill-Reports schreiben.

### Phase 6 - provenance last
1. Alle Non-Report-Artefakte finalisieren.
2. Finalen Tree-Digest pro Skill berechnen.
3. Neue Run-ID/Evidence-Epoch erzeugen.
4. `DRAFT_FROZEN` und alle nachfolgenden Events an denselben Digest binden.
5. Release Report, Enterprise Evaluator und Validation Report neu erzeugen.
6. `VALIDATION_PASSED` und erst danach `PACKAGE_AUTHORIZED` schreiben.
7. Beide Ledger validieren und beide Skills als `skill.zip` paketieren.

## Validation gates

- Gate A Truth: 8/8 plus cross-skill Truth-Attack PASS.
- Gate B Contract: v1.3 96/96 roles, v1/v1.1/v1.2 regressions PASS.
- Gate C Consumer: 96/95 compile/receipt/harness PASS.
- Gate D Pair: exact version/digest/header parity against actual installed peer.
- Gate E Release: all negative mutations blocked.
- Gate F Provenance: both final ledgers PASS on final tree digests.

## Rollback

v1.3 is additive. Rollback selects v1.2/v1.1/v1 or reverts the paired release. Never alter historical contract bytes, weaken failing assertions, manually rewrite digests into reports, or authorize live calling from a local/static test.
