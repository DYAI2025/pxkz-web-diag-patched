# Pixelkiez Batch Contract v1.3 Role Matrix

This matrix is generated from the canonical v1.3 contract. The role is the only normative requiredness axis in v1.3.

| # | Field | Authority | Missing semantics | v1.3 role | Default allowed | Blocks upload | Blocks production |
|---:|---|---|---|---|---|---|---|
| 0 | `phone_number` | ElevenLabs transport | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_REQUIRED` | no | yes | no |
| 1 | `recipient_number` | Internal / dynamic variable | `REQUIRED_MIRROR_IF_PHONE_PRESENT_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 2 | `campaign_id` | Campaign | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 3 | `lead_id` | CRM / lead pipeline | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 4 | `customer_name` | Lead record | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 5 | `customer_salutation` | Lead record | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 6 | `customer_website` | Lead/audit input | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 7 | `website_language` | Website audit | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 8 | `customer_language` | Campaign/lead approval | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 9 | `customer_locale` | Campaign/lead | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 10 | `restaurant_name` | Lead record | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 11 | `customer_role` | Lead record | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 12 | `city` | Lead record | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 13 | `district` | Lead record | `BLANK_IF_UNKNOWN_OR_NOT_APPLICABLE_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 14 | `restaurant_category` | Lead/audit | `BLANK_IF_UNKNOWN_OR_NOT_APPLICABLE_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 15 | `cuisine_type` | Lead/audit | `BLANK_IF_UNKNOWN_OR_NOT_APPLICABLE_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 16 | `prospect_company` | Alias / build compatibility | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 17 | `prospect_role` | Alias / build compatibility | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 18 | `prospect_locale` | Alias / build compatibility | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 19 | `website_role` | Campaign context | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 20 | `primary_customer_type` | Campaign context | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 21 | `lead_source_current` | Compliance input | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 22 | `compliance_status` | Compliance owner | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 23 | `do_not_contact` | Compliance/CRM | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 24 | `jurisdiction` | Compliance | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 25 | `contact_type` | Compliance | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 26 | `ai_disclosure_required` | Policy | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 27 | `recording_status` | Compliance | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `PRODUCTION_GATE_ONLY` | no | no | yes |
| 28 | `audit_id` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 29 | `audit_date` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 30 | `audit_method_scope` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 31 | `audit_overall_score` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 32 | `audit_score_scale` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 33 | `audit_score_status` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 34 | `audit_limitations` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 35 | `audit_strength_1_observation` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 36 | `audit_strength_1_evidence_pointer` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 37 | `audit_strength_1_confidence` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 38 | `audit_hook_1_id` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 39 | `audit_hook_1_dimension` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 40 | `audit_hook_1_priority` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 41 | `audit_hook_1_evidence_class` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 42 | `audit_hook_1_observation` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 43 | `audit_hook_1_evidence_pointer` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 44 | `audit_hook_1_confidence` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 45 | `audit_hook_1_spoken` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 46 | `audit_hook_1_possible_relevance` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 47 | `audit_hook_1_prohibited_claims` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `INTERNAL_RECORD` | no | no | no |
| 48 | `audit_hook_1_selector_score` | Compiler output | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 49 | `audit_hook_2_id` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 50 | `audit_hook_2_dimension` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 51 | `audit_hook_2_priority` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 52 | `audit_hook_2_evidence_class` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 53 | `audit_hook_2_observation` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 54 | `audit_hook_2_evidence_pointer` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 55 | `audit_hook_2_confidence` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 56 | `audit_hook_2_spoken` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 57 | `audit_hook_2_possible_relevance` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 58 | `audit_hook_2_prohibited_claims` | Validated audit packet | `BLANK_ALLOWED_WARN_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 59 | `audit_hook_2_selector_score` | Compiler output | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 60 | `audit_hook_3_id` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 61 | `audit_hook_3_dimension` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 62 | `audit_hook_3_priority` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 63 | `audit_hook_3_evidence_class` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 64 | `audit_hook_3_observation` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 65 | `audit_hook_3_evidence_pointer` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 66 | `audit_hook_3_confidence` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 67 | `audit_hook_3_spoken` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 68 | `audit_hook_3_possible_relevance` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 69 | `audit_hook_3_prohibited_claims` | Validated audit packet | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 70 | `audit_hook_3_selector_score` | Compiler output | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 71 | `call_stage` | Conversation state | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 72 | `interest_level` | Conversation state | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 73 | `confirmed_relevance` | Conversation state | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 74 | `meeting_readiness` | Conversation state | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 75 | `preferred_followup_time` | Conversation state | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 76 | `opt_out` | Conversation state | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 77 | `needs_human` | Conversation state | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 78 | `meeting_offer` | Campaign/meeting contract | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 79 | `meeting_timezone` | Campaign/meeting contract | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `OPTIONAL` | no | no | no |
| 80 | `consultant_id` | Campaign/meeting contract | `BLANK_ALLOWED_DO_NOT_INFER` | `INTERNAL_RECORD` | no | no | no |
| 81 | `meeting_duration_minutes` | Campaign/meeting contract | `BLANK_ALLOWED_DO_NOT_INFER` | `OPTIONAL` | no | no | no |
| 82 | `customer_email` | CRM_OR_VERIFIED_PROSPECT_CONTACT | `Blank means unknown or not supplied. Never infer from a domain or company name; ask only after the prospect accepts the analysis-send fallback.` | `OPTIONAL` | no | no | no |
| 83 | `company_name` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_REQUIRED` | no | yes | no |
| 84 | `company_website` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_REQUIRED` | no | yes | no |
| 85 | `prospect_name` | Lead / verified public business contact | `REQUIRED_NON_EMPTY_SAFE_SENTINEL` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 86 | `prospect_salutation` | Lead / generic safe fallback | `REQUIRED_NON_EMPTY_SAFE_FALLBACK` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 87 | `call_compliance_status` | Compliance owner / compatibility alias | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 88 | `call_compliance_note` | Compliance compatibility note | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 89 | `lead_source` | Compliance / lead pipeline | `REQUIRED_NON_EMPTY_SAFE_SENTINEL` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 90 | `consultant_name` | Meeting contract / safe role fallback | `REQUIRED_NON_EMPTY_SAFE_FALLBACK` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 91 | `meeting_description` | Campaign / meeting contract | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 92 | `offer_process` | Approved Pixelkiez company contract | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 93 | `website_analysis_report` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 94 | `agency_name` | Approved Pixelkiez company contract | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |
| 95 | `verified_finding` | Validated audit packet | `REQUIRED_NON_EMPTY_FAIL_CLOSED` | `EL_RUNTIME_DEFAULTED` | yes | yes | no |

## Deterministic default policies

- `agency_name`: Pixelkiez
- `call_compliance_note`: deterministic note that the website audit does not grant legal call approval
- `call_compliance_status`: LEGAL_REVIEW_REQUIRED unless authoritative compliance_status is supplied
- `call_stage`: PRECALL_GATE
- `confirmed_relevance`: false
- `consultant_name`: Pixelkiez Beratungsteam role fallback; not a fabricated individual
- `interest_level`: unknown
- `lead_source`: NICHT_VERIFIZIERT when authoritative lead source is absent; never spoken as fact
- `meeting_description`: approved generic Pixelkiez analysis/next-steps description
- `meeting_readiness`: unknown
- `needs_human`: false
- `offer_process`: approved Pixelkiez process fallback from company contract
- `opt_out`: false
- `prospect_name`: NICHT_VERIFIZIERT when no verified person is available; never spoken as a factual name
- `prospect_salutation`: Guten Tag generic safe fallback
- `recipient_number`: mirror phone_number exactly
- `verified_finding`: non-factual sentinel when no derived VERIFIED_FACT exists
- `website_analysis_report`: deterministic audit-id/report/score-status summary

## Production gate rules

- `ai_disclosure_required`: must be explicitly present as true/false
- `compliance_status`: must equal APPROVED
- `contact_type`: non-empty authoritative contact type
- `customer_language`: non-empty authoritative campaign/lead language
- `do_not_contact`: must equal false
- `jurisdiction`: non-empty authoritative jurisdiction
- `lead_source_current`: non-empty authoritative compliance/lead source
- `recording_status`: must be OFF or APPROVED
