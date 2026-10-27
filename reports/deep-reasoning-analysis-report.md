# Pixelkiez Website Diagnosis - Measurement Enrichment and Customer Activation Analysis

## Decision summary

The research supports a production-oriented extension, but not by inflating the existing 48-metric score model. The safest architecture is an **optional measurement-enrichment layer** that can attach authenticated Google data, public lab/field performance data, query-specific SERP observations, and browser-observed accessibility/privacy signals to the canonical audit. The existing score, truth discipline, four-lever selection, batch v1.3 wire contract, and customer-language firewall remain unchanged.

The presentation needs two direct corrections:

1. Replace the ambiguous low-score label `offen` with a four-state customer status model: `Klar`, `Verbesserung sinnvoll`, `Handlungsbedarf`, `Nicht belastbar bewertet`. `Handlungsbedarf` uses a strong X/coral signal only for an evidenced weakness. It must never be interpreted as a legal determination.
2. Remove the negative closing page (`Grenzen` / `Noch offen`). Replace it with an action-oriented closing: what Pixelkiez will do, how the next step works, and how improvement will be re-measured. Material qualification stays attached to the relevant metric/visual or in internal reports, not as the final customer frame.

## Evidence and claim boundaries

### Supported as production adapter candidates

- Google Search Console Search Analytics: query/page/device/country dimensions with clicks, impressions, CTR and average position. Results are bounded by Search Console limits and do not guarantee every row.
- Search Console URL Inspection: index verdict/state, robots state, fetch state, crawl timestamp, Google/user canonical and sitemap context for the indexed version.
- Google Analytics Data API `runReport`: authenticated property reports including active users, sessions and configured event counts. GA4 aggregate events are not equivalent to qualified leads.
- PageSpeed Insights API: current Lighthouse lab measurements; field data must be treated separately.
- Chrome UX Report API: real-user Chrome field metrics when the URL/origin has sufficient data.
- DataForSEO Google Organic Live Advanced: query-, location-, language- and device-specific SERP observations. `rank_group`/`rank_absolute` are source-specific observations; a Google result-page number is shown only if the provider explicitly returns one.
- Browser automation with Playwright/Chromium: public-state inspection of requests, storage, cookies, consent controls, forms, keyboard focus and responsive overflow.

### Supported only with boundaries

- Automated accessibility checks can surface defects but cannot prove complete WCAG conformance. Human evaluation remains necessary.
- Privacy/consent browser evidence can prove technical observations (for example, third-party requests before a choice) but cannot by itself prove illegality or select the correct legal basis.
- Search visibility has no single stable domain rank. Customer ranking statements require the concrete query, location/market, device, timestamp and method.
- GA4 `phone_click` proves a click event only; `form_submit` proves a submit event only; qualified lead/customer states require backend/CRM evidence.

## Architecture options

### Option A - add all new metrics to the scored 48-metric registry

Rejected. Missing customer credentials or provider quotas would directly change score coverage and make historical comparisons unstable. External provider semantics would become score dependencies.

### Option B - create a second audit engine

Rejected. It duplicates evidence, scoring, customer-story and PDF logic and creates reconciliation drift.

### Option C - optional enrichment layer before business interpretation

Adopted. New measurement records carry provenance and availability state, can enrich benchmark/ranking/user-data sections and future findings, but do not alter the existing score unless a separately versioned scoring migration is approved later.

## Canonical enrichment metric families

- Search: current SERP position, Search Console average position, impressions, clicks, CTR, index verdict/canonical state.
- Performance: PSI Lighthouse lab score/LCP/CLS, CrUX LCP/INP/CLS p75 when available.
- Audience/Funnel: GA4 active users, sessions, configured event counts (`primary_cta_click`, `form_start`, `form_submit`, `phone_click`) with explicit proxy boundaries.
- Accessibility: automated critical/serious findings when an axe runtime is supplied; deterministic DOM/accessibility-name/focus/overflow observations otherwise; manual review required.
- Privacy/Consent: consent controls detected, third-party requests before choice, cookies/storage before choice, accept/reject state deltas. Technical review only.

Each record must include source/provider, observation time, date range where relevant, URL/query/location/device where relevant, value/unit, status, evidence reference and claim boundary. Credentials are runtime inputs only and must never be serialized.

## Customer semiotics

| State | Symbol | Customer meaning | Allowed trigger |
|---|---|---|---|
| Klar | check | no relevant weakness in assessed scope | scored/observed strength |
| Verbesserung sinnvoll | ! | supported opportunity, not urgent | measured/observed moderate weakness |
| Handlungsbedarf | X | supported material weakness requiring action | measured/observed weak/blocking result |
| Nicht belastbar bewertet | neutral | insufficient evidence | not_assessed/unavailable |

For privacy/accessibility, `Handlungsbedarf` means the technical evidence supports remediation. It is **not** a legal or certification statement.

## Closing page target

The customer PDF must finish with agency and action:

- title: `Aus Analyse wird Umsetzung.`
- short statement: four levers are translated into concrete changes.
- 3-step path: `Priorisieren -> Umsetzen -> Nachmessen`.
- CTA: `Prioritäten bestätigen und Umsetzung starten.`
- footer: one short data-context sentence only when needed; no list of missing capabilities.

## Failure modes and controls

1. Missing credential -> invented metric. Control: `NOT_CONFIGURED/UNAVAILABLE`, null value, no customer number.
2. Search Console average position -> presented as current rank. Control: separate metric IDs and source labels.
3. Lighthouse -> presented as real-user performance. Control: LAB vs FIELD classes and explicit source boundary.
4. Phone click -> presented as lead. Control: event semantic registry and `does_not_prove`.
5. Browser privacy observation -> presented as legal violation. Control: technical status only; legal review flag internal.
6. Automated accessibility -> presented as WCAG certification. Control: mandatory manual-review boundary.
7. Dramatic color -> sales pressure without evidence. Control: status resolver uses measurement class/status/score only; not-assessed is grey.
8. Final slide undermines action. Control: customer schema v8 requires `closing` and prohibits `client_limits`.

## Architecture gate recommendation

**PASS_WITH_ASSUMPTIONS**

Proceed with the enrichment layer, customer-status resolver and closing-page redesign. Live authenticated provider calls cannot be end-to-end verified in this build because no customer Google/DataForSEO credentials were supplied. Those adapters must therefore be fixture-validated, fail closed without credentials, and report runtime capability state truthfully. Browser automation can be locally verified against a controlled fixture using system Chromium.
