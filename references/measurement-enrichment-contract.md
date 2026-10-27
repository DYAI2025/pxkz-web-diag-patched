# Measurement Enrichment Contract

## Purpose

Pixelkiez may enrich the canonical public website diagnosis with additional measured data. Enrichment records are optional, provenance-bearing and fail-closed and remain non-scoring **as enrichment records**. Missing credentials, missing traffic volume or unavailable runtimes never become zero values and never directly change the core score. Under the separate Active Core Migration, a normalized enrichment observation may be cited by a Core Execution result only through the explicit binding and Score Admission Gate; no provider/enrichment row is injected directly into scoring.

## Data classes

1. **PUBLIC_MEASUREMENT** — PageSpeed Insights, CrUX where available, public SERP measurement, public Chromium/Playwright observation.
2. **USER_AUTHORIZED_MEASUREMENT** — Google Search Console and Google Analytics 4 read-only access supplied or authorized for the audited property.
3. **FUTURE_FIRST_PARTY_TELEMETRY** — event instrumentation, BigQuery event journeys and first-party Web Vitals/RUM. Historical events that were never collected must not be reconstructed as fact.

Every enrichment metric carries source type/provider, observation time, target URL, and when relevant query, location, market, device and date range. Internal fields may also carry manual/legal review requirements and claim boundaries.

## Supported adapters

- **PageSpeed Insights API**: lab-oriented page analysis. Preserve device/strategy and never label Lighthouse lab output as real-user field data.
- **Chrome UX Report API**: real-user Chrome experience when Google has a sufficiently populated record. If URL-level data is unavailable, an origin record may be used only when explicitly labelled as origin-level data. Missing CrUX data is `UNAVAILABLE`, not a performance failure.
- **Search Console Search Analytics API**: authorized historical search performance including clicks, impressions, CTR and average position. Average position is not a live rank.
- **Search Console URL Inspection API**: authorized index/inspection evidence. It must not be generalized beyond inspected URLs.
- **GA4 Data API**: authorized reporting for tracked events/metrics. `phone_click` is not a phone call; form submission is not a qualified lead; a qualified lead requires a corresponding authoritative downstream signal.
- **SERP adapter**: current query/location/device-bound search snapshot. A Google result-page number is customer-visible only when the provider returns an explicit page field; do not derive a page number from position.
- **Chromium/Playwright public browser module**: public-state observation only. It may compare pre-choice/accept/reject browser states, visible consent controls, cookies/storage/network destinations, keyboard focus samples, unnamed controls and mobile overflow. It must not access authenticated/private areas or submit irreversible forms.

## Security and credentials

Credentials are runtime inputs only and must never be written into reports, fixtures, receipts, ZIPs or logs. Supported environment names are:

- `PIXELKIEZ_PAGESPEED_API_KEY`
- `PIXELKIEZ_CRUX_API_KEY`
- `PIXELKIEZ_GOOGLE_ACCESS_TOKEN`
- `PIXELKIEZ_DATAFORSEO_LOGIN`
- `PIXELKIEZ_DATAFORSEO_PASSWORD`
- optional `PIXELKIEZ_CHROMIUM_PATH`

The network adapter allowlists only its documented provider hosts. The browser module remains public-only. User-authorized BigQuery analysis is represented as an SQL template; this Skill does not store BigQuery credentials or create OAuth flows.

## Measurement truth rules

- Current SERP position and Search Console average position are separate truths and must never be merged into one rank.
- SERP statements require query context; current-position customer visuals additionally require location, device and observation time.
- PageSpeed/Lighthouse values are lab data. CrUX/RUM values are field data.
- GA4 only proves events that were actually tracked. Never infer missing historical events.
- Accessibility automation/interactions can surface barriers but do not prove complete WCAG conformance. Manual evaluation remains a separate layer.
- Privacy/consent browser observations may establish technical `Handlungsbedarf`; they do not establish legal unlawfulness.
- Missing API access, sparse samples, rate limits or runtime policy are explicit source states, never invented values.

## Canonical integration

`measurement_enrichment` is attached to the canonical scored report as an optional object and then copied into `analysis_report.json` and `analysis_report.md`. The enrichment registry remains separate from the exact 48 canonical metric IDs. Any active use of enrichment evidence must be promoted through `schemas/core-execution-bundle.schema.json`, `assets/core-evidence-bindings.active.v1.json` and the Score Admission Gate before a canonical core row exists.

Customer projection may use up to three measured highlights, for example a query-specific live SERP position, GA4 active users for a dated period, or CrUX p75 LCP. Customer-visible values must retain the context required to interpret them correctly.

## BigQuery journey template

`assets/sql/ga4_journey_events.sql` is a starting template for user-authorized GA4 BigQuery exports. It is not executed without an authorized dataset. Event names preserve semantic boundaries between CTA clicks, form starts, form submits, phone clicks and downstream lead states.


## Optional Measurement Gateway integration

A separately executed Pixelkiez Measurement Gateway may supply bounded public HTTP/TLS/CSP/robots/sitemap observations through `schemas/measurement-envelope.schema.json`. The envelope is validated and mapped only to approved `PUBLIC_*` enrichment metrics. These records remain `NON_SCORING_ENRICHMENT` in their native enrichment path. A separately created Core Execution result may cite an eligible normalized observation and attempt active admission; the native Gateway/enrichment record itself is still never a score row.

Gateway absence, target-policy rejection or runtime/network failure is an explicit unavailable source state, never numeric zero. Raw response bodies are not copied into the report; gateway provenance uses run IDs, adapter identity, timestamps, claim boundaries and response digests. Continuous monitoring and owner analytics remain separate contracts because a one-shot public probe cannot establish uptime or reconstruct historical user behavior.
