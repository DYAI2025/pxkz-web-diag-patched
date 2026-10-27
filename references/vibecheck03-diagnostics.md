# Vibe-Check #03 — bounded, non-scoring diagnostic contract

This extension is **offline/fixture-capable, not a complete live-browser or live-probe implementation**. It reads pre-acquired permitted page HTML and optional separately verified external asset, 404 or isolated UI scenario observations. It performs **zero network requests**, writes only a requested output file, and never creates customer findings itself. A dynamic runtime/secure HTTP acquisition adapter is still not implemented. Customer admission is a separate, opt-in attach step (see *Customer projection*).

## Families and interpretation

- VC03-01: favicon declaration, verified icon asset and optional Apple touch icon. Tab title remains canonical FIND-06. Declaration is not browser-display proof. A missing optional Apple icon is not a negative finding.
- VC03-02: four OGP base tags (title/type/url/image), optional description and verified image delivery. HTML meta description is distinct; platform preview rendering remains unverified.
- VC03-03: separate authorization-gated externally supplied 404 scenario. HTTP 200 is observed status, not Google soft-404 classification. A generic usable page is not automatically defective. Without a verified probe, NOT_ASSESSED.
- VC03-04: integer image counts: missing alt, empty alt, nonempty alt. Coverage may be derived only for complete sample and positive image count. Empty alt can be correct for decorative images. Nonempty alt does not establish meaning; no WCAG claim. Reuse A11Y-03 and FIND-09 rather than score again.
- VC03-05: requires isolated authorized scenario with initial state, action, observed state and measured accessible announcement. Without scenario, NOT_ASSESSED. Attribute presence alone cannot verify announcement. Existing UX-08 scoring remains independent.

## Execution

`python scripts/vibecheck03.py preacquired-input.json diagnostics.json`

Input requires `run_id`, `page_url`, `html`, `html_complete` (full selected-page sample), `observed_at`; optional `asset_results` mapping absolute public URLs to separately verified booleans; optional `unknown_route` with `authorized`, `same_origin`, `bounded`, `url`, integer `http_status`, and boolean navigation observations; optional `ui_scenario` with `authorized`, `isolated`, `scenario_id`, `initial_state`, `action`, `observed_state`, boolean observations. No external URL is fetched by this command. DNS and redirect security remain responsibility of approved acquisition runtime; flag DNS unverified, never execute it here.

Output has 20 stable metrics, one authority and run/page binding, unique evidence refs, `OBSERVED`/`NOT_ASSESSED`, no score effect, and no admitted customer findings. Existing 48 Core metric IDs and score processing remain immutable.

Parser note: `<link>`/`<meta>` count when inside `<head>` or before the first body element (HTML5 implied head); metadata inside the body does not count. The input key is `ui_scenario` (one object); the plural `ui_scenarios` is rejected instead of silently ignored.

## Customer projection (route `VC03_DIAGNOSTIC`, opt-in)

`python scripts/attach_vibecheck03_findings.py scored-report.json diagnostics.json attached-report.json`

The attach step embeds the validated block as `report.vibecheck03` and derives candidate findings only from the versioned rule table `assets/vibecheck03-customer-admission-rules.v1.json`. It refuses a block whose `page_url` is not exactly one of the audited pages (`meta.audited_url` or `coverage.sampled_pages`, compared by scheme, host, effective port, path and query), a report without `meta.audit_id` (`VC03_RUN_UNBOUND`) or with a different one (`VC03_RUN_MISMATCH`), any `OBSERVED` value that does not match its catalog type (`BOOLEAN` = true/false, `INTEGER` = non-negative integer; `VC03_VALUE_TYPE_INVALID`), and any authority other than `STANDALONE_OFFLINE`. Metrics, score and categories stay byte-identical; re-running is idempotent.

Customer-candidate rules (severity `low`, confidence 3, no `metric_refs`, no `customer_risk`):

| Rule | Defect condition (all cited rows `OBSERVED`) | Category |
|---|---|---|
| `VC03-R-ICON-UNAVAILABLE` | `SITE_ICON_FETCH_OK = false` | trust_privacy_content |
| `VC03-R-PREVIEW-INCOMPLETE` | any of og:title/type/url/image `= false` (complete sample) | findability_seo |
| `VC03-R-PREVIEW-IMAGE-UNAVAILABLE` | og:image declared, `OG_IMAGE_FETCH_OK = false` | findability_seo |
| `VC03-R-ERROR-PAGE-NO-HOME` | authorized unknown route HTTP 404/410 and no home link | ux_conversion |
| `VC03-R-ALT-MISSING` | `0 < IMG_ALT_MISSING_COUNT <= IMG_ELEMENT_COUNT` (complete sample) | accessibility |

Internal only: HTTP 200 on an unknown route (`SOFT_404_HYPOTHESIS_INTERNAL_ONLY`), UI scenario observations (`MANUAL_REVIEW_REQUIRED`), missing contact link alone, empty alt attributes, every `NOT_ASSESSED` row.

`strategic_relevance.evaluate_finding` routes any finding with `vibecheck03_diagnostic` evidence exclusively through `VC03_DIAGNOSTIC` (a core-metric link cannot be borrowed); only a fully valid legal sidecar route (legal evidence plus Impressum `customer_risk`) keeps precedence, so mandatory legal levers are never displaced. Re-attaching replaces only earlier derived findings (VC03 evidence only, no `customer_risk`). Rejection reasons: `VC03_BLOCK_MISSING`, `VC03_BLOCK_AUTHORITY`, `VC03_BLOCK_PAGE_NOT_AUDITED_SITE`, `VC03_RUN_UNBOUND`, `VC03_RUN_MISMATCH`, `VC03_VALUE_TYPE_INVALID`, `VC03_BLOCK_CONFLICT`, `VC03_EVIDENCE_UNRESOLVED`, `VC03_PAGE_MISMATCH`, `VC03_VALUE_CONFLICT`, `VC03_NO_MATCHING_RULE`, `VC03_RULE_NOT_SATISFIED`, `VC03_SOURCE_CONFLICT` (same metric from a second source, never merged), `VC03_DUPLICATE_OBSERVATION`, `VC03_CORE_METRIC_REFS_FORBIDDEN`, `VC03_CUSTOMER_RISK_FORBIDDEN`, `VC03_SEVERITY_CAP`, `VC03_NO_RETEST`, `VC03_NO_BUSINESS_MECHANISM`, `VC03_FORBIDDEN_CLAIM` (percentages, revenue, conversion, legal certainty, platform/ranking claims).

Eligible VC03 findings then compete in the unchanged lever selection: legal mandatory and critical/high findings stay ahead, at most four levers. Customer copy comes from fixed German templates and observed counts only; page text is never copied. The internal report records `vibecheck03_admission` (eligible, rejected with reasons, internal-only, not assessed; `not_assessed_is_negative: false`). End-to-end proof: `scripts/run_vc03_customer_release_evals.py`.

## PXAPI migration

`PXAPI_CANONICAL` is only an input authority claim, not itself verification. Do not merge parallel Skill and PXAPI facts. Compare separately and reject conflicts; actual PXAPI contract adapter is not yet implemented. `STANDALONE_OFFLINE` means legacy fallback, not API parity.

## Safety and retesting

Source is user-provided draft plus open-standard references; verify standards before treating external details as normative. Never auto-submit production forms, brute-force unknown routes, fetch unsafe assets, or interpret unavailable results as negative site quality. Retest against the exact page and declared scenario after a supervised fix. Preserve source and method versions.
