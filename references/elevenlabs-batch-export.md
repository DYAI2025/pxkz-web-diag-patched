# Pixelkiez ElevenLabs Batch Export Contract

## Versions

- v1: 82 legacy fields.
- v1.1: 83 fields, adding optional `customer_email`.
- v1.2: 96 fields, adding the 13 exact Dynamic Variables observed as required by the current ElevenLabs agent upload gate on 2026-08-28.
- v1.3: 96 fields, default. The CSV column names and order are exactly the same as v1.2; v1.3 changes readiness semantics by classifying every field exactly once.

## v1.3 five-class model

| Class | Meaning | Missing value effect |
|---|---|---|
| `INTERNAL_RECORD` | Audit/business trace retained for handoff and evidence | Never blocks ElevenLabs upload readiness |
| `EL_RUNTIME_REQUIRED` | No safe generic default exists | Missing blocks ElevenLabs upload readiness |
| `EL_RUNTIME_DEFAULTED` | Compiler must materialize verified or deterministic safe/fail-closed value | Missing after compilation blocks upload readiness |
| `OPTIONAL` | Helpful but not required | Blank is valid and never blocks upload readiness |
| `PRODUCTION_GATE_ONLY` | Authoritative Campaign/CRM/Compliance/Meeting input | Missing blocks only the separate production prerequisite gate |

Current classification counts are:

- `INTERNAL_RECORD`: 48
- `EL_RUNTIME_REQUIRED`: 3
- `EL_RUNTIME_DEFAULTED`: 18
- `OPTIONAL`: 14
- `PRODUCTION_GATE_ONLY`: 13

The three `EL_RUNTIME_REQUIRED` fields are `phone_number`, `company_name`, `company_website`.

`customer_email` is `OPTIONAL`. An unknown email address must stay blank and must never make an otherwise upload-ready row invalid.

`prospect_name` is `EL_RUNTIME_DEFAULTED`, not source-required. When no verified human name exists, the compiler uses the non-spoken sentinel `NICHT_VERIFIZIERT`. `prospect_salutation` safely falls back to `Guten Tag`.

## Current-agent compatibility

The 13 Dynamic Variable names observed on 2026-08-28 remain non-empty in compiler-built v1.3 rows because they are either runtime-required or runtime-defaulted:

`company_name`, `company_website`, `prospect_name`, `prospect_salutation`, `call_compliance_status`, `call_compliance_note`, `lead_source`, `consultant_name`, `meeting_description`, `offer_process`, `website_analysis_report`, `agency_name`, `verified_finding`.

Safe/fail-closed rules:

- `call_compliance_status`: mirror authoritative `compliance_status` when present; otherwise `LEGAL_REVIEW_REQUIRED`, never `APPROVED`.
- `call_compliance_note`: deterministic limitation note.
- `lead_source`: verified source or non-spoken `NICHT_VERIFIZIERT`.
- `consultant_name`: verified person when supplied or role label `Pixelkiez Beratungsteam`.
- `agency_name`: `Pixelkiez`.
- `website_analysis_report`: derived from the validated audit artifact.
- `verified_finding`: verified finding when available, otherwise a safe no-finding sentence; never invent a claim.

## Gates

`elevenlabs_upload_status=EL_UPLOAD_READY` means the row passed structural/type checks and every `EL_RUNTIME_REQUIRED` + `EL_RUNTIME_DEFAULTED` field is non-empty after compilation.

`production_prerequisite_gate=PASS` means all `PRODUCTION_GATE_ONLY` fields were supplied by authorized sources and existing fail-closed compliance consistency checks passed.

Neither gate proves provider acceptance, legal eligibility, live-call authorization, conversation quality, booking success, or business outcome. `live_call_production_status` remains `NOT_ASSESSED` in this skill.

## Auto-detection

v1.2 and v1.3 intentionally share the same 96-column header. Header-only auto-detection resolves that shape to the latest default v1.3 semantics. To validate historical v1.2 readiness semantics, select `--contract-version v1.2` explicitly.

## Commands

```bash
python scripts/build_elevenlabs_batch_csv.py diagnosis-report-scored.json pixelkiez_elevenlabs_batch.csv --validation-out pixelkiez_elevenlabs_batch.validation.json
python scripts/validate_elevenlabs_batch_csv.py pixelkiez_elevenlabs_batch.csv --require-elevenlabs-upload-ready
python scripts/validate_elevenlabs_batch_csv.py pixelkiez_elevenlabs_batch.csv --require-production-prerequisites

# compatibility modes
python scripts/build_elevenlabs_batch_csv.py diagnosis-report-scored.json old-v12.csv --contract-version v1.2
python scripts/build_elevenlabs_batch_csv.py diagnosis-report-scored.json old-v11.csv --contract-version v1.1
python scripts/build_elevenlabs_batch_csv.py diagnosis-report-scored.json old-v1.csv --contract-version v1
```
