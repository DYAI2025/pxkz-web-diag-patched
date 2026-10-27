# Pixelkiez Website Diagnosis

Enterprise Website-Diagnosis-Skill für öffentliche Business-Websites. Der Skill erzeugt aus einer kanonischen, evidenzgebundenen Diagnose zwei kontrollierte Projektionen:

1. `client-report-model.json` -> `pixelkiez-website-analysis.pdf` für den Kunden.
2. `pixelkiez_elevenlabs_batch.csv` + Validation Sidecar für den nachgelagerten Pixelkiez Audit-/CRM-/Compliance-/Voice-Handoff.

## Pflichtartefakte je completed audit

- `diagnosis-report.json`
- `client-report-model.json`
- `pixelkiez-website-analysis.pdf`
- `pixelkiez-website-analysis.visual-qa.json` (PASS erst nach echter seitenweiser Sichtprüfung; an PDF-SHA-256 gebunden)
- `pixelkiez_elevenlabs_batch.csv`
- `pixelkiez_elevenlabs_batch.validation.json`
- relevante Validator-/Eval-Reports

Neue Batch-Exports verwenden standardmäßig v1.3 mit unverändert 96 Spalten. Alle Felder sind genau einer von fünf Klassen zugeordnet: `INTERNAL_RECORD`, `EL_RUNTIME_REQUIRED`, `EL_RUNTIME_DEFAULTED`, `OPTIONAL`, `PRODUCTION_GATE_ONLY`. `customer_email` ist `OPTIONAL`; unbekannter Ansprechpartner wird über sichere Runtime-Defaults abgefangen. Fehlende optionale/interne/produktionsbezogene Daten blockieren nicht die ElevenLabs-Upload-Readiness.

## Batch Contract

- Default: v1.3 / 96 fields / five-class readiness model / identical v1.2 wire header
- Additive field: optional `customer_email`
- Legacy: v1 / 82 fields
- Default v1.1 SHA-256: `ab5570bac1066d4c999a0e8f9b674a9ebfb13eccfabbb1cd0fd049400f0cec5a`
- Legacy Website v1 SHA-256: `66018327ad7480c44e17cf071e6e864105f7d9185d4965cafbd76f9c168edfe5`
- Excluded special overrides: `language`, `first_message`, `system_prompt`, `voice_id`
- Voice context: at most three evidence-bound audit hooks; no technical consulting payload

## Local validation

```bash
python scripts/quick_validate.py .
python scripts/validate_batch_contract.py .
python scripts/run_batch_contract_evals.py .
python scripts/run_fixture_eval.py .
python scripts/validate_release_gate.py .
python scripts/validate_pipeline_ledger.py .
```

## Boundary

In v1.3, `elevenlabs_upload_status=EL_UPLOAD_READY` means only that structural/type checks plus runtime-required/defaulted completeness passed. `production_prerequisite_gate` is separate. Legacy `batch_status=BATCH_READY` remains only as an alias of upload readiness and is not production readiness. None of these states proves legal eligibility, provider acceptance, agent behavior, booking success, or live-calling authorization.

## Verbindliches PDF-/Diagramm-Template

Der Standard-Kundenbericht ist eine kurze Marketing-Zusammenfassung: maximal vier Verbesserungshebel, zwei bis drei V01-V11-Diagramme, höchstens zwölf Seiten und kein technischer Metrik-/Quellenanhang. Die vollständige Evidenz bleibt in JSON/Sidecars erhalten. V12 bleibt Teil der internen Diagrammbibliothek, wird aber nicht im Standard-Kunden-PDF verwendet.

`assets/PXK_web_audit_template.pdf` (Stand 27.08.2026) ist im Skill gebündelt und bildet zusammen mit `templates/chart-library.v1.json` den verbindlichen V01-V12-Diagrammvertrag. Jeder ausführende Agent nutzt dieselben Datenformen, Evidenz-/Populationsangaben, Schwellenregeln und den sichtbaren `Beweist nicht`-Block. Die Chart-Payloads werden deterministisch validiert; danach wird der PDF-Output seitenweise als Bild geprüft. `create_pdf_visual_qa_manifest.py` startet bewusst fail-closed mit `PENDING`; nur ein Agent mit realer Bildsicht oder ein Mensch darf nach Prüfung auf `PASS` setzen. `validate_pdf_visual_qa.py` bindet den QA-Bericht an exakt den finalen PDF-Digest.


## ElevenLabs current-agent binding v1.3

The 2026-08-28 observed upload gate requires 13 exact Dynamic Variable names. v1.3 keeps the same 96-column header as v1.2 and ensures those 13 are either runtime-required or compiler-defaulted. Unknown prospect/lead facts use non-spoken sentinels; compliance aliases fail closed to `LEGAL_REVIEW_REQUIRED`. Production/compliance authority fields remain separate `PRODUCTION_GATE_ONLY` inputs.


## Optional Measurement Gateway

The Skill can consume a separately deployed, read-only Pixelkiez Measurement Gateway through a versioned JSON envelope. The package itself remains fully functional without that runtime. Public gateway evidence is normalized into existing non-scoring enrichment; missing gateway availability never becomes score zero. The first companion gateway slice covers bounded public HTTP/redirect, HTTPS/TLS, robots/sitemap, selected security-header and CSP observations with fail-closed target/redirect validation. Continuous monitoring, first-party analytics and MCP remain optional follow-on adapters behind separate contracts.
