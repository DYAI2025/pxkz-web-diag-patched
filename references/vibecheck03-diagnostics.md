# Vibe-Check #03 — bounded, non-scoring diagnostic contract

This extension is **offline/fixture-capable, not a complete live-browser or live-probe implementation**. It reads pre-acquired permitted page HTML and optional separately verified external asset, 404 or isolated UI scenario observations. It performs **zero network requests**, writes only a requested output file, and does not create customer findings. A dynamic runtime/secure HTTP acquisition adapter and customer evidence-admission integration require additional work and test evidence before release.

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

## Customer projection

Do not add a customer finding from these rows automatically. Required future adapter: validate evidence id/run/page, directly observed status, business mechanism, proportionate action and retest; then route through existing Strategic Relevance and legal priority, retaining four levers. Without this integration the extension is internal-only, and customer release is blocked.

## PXAPI migration

`PXAPI_CANONICAL` is only an input authority claim, not itself verification. Do not merge parallel Skill and PXAPI facts. Compare separately and reject conflicts; actual PXAPI contract adapter is not yet implemented. `STANDALONE_OFFLINE` means legacy fallback, not API parity.

## Safety and retesting

Source is user-provided draft plus open-standard references; verify standards before treating external details as normative. Never auto-submit production forms, brute-force unknown routes, fetch unsafe assets, or interpret unavailable results as negative site quality. Retest against the exact page and declared scenario after a supervised fix. Preserve source and method versions.
