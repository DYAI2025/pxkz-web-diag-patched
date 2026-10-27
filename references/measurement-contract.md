# Pixelkiez Website Measurement Contract

## Purpose

This contract combines the existing Pixelkiez evidence-first audit with the reusable method components from the Website Intelligence Auditor. It defines what an audit should attempt, how each result is classified, and when a result may influence the Pixelkiez score.

## Two independent evidence axes

Every metric record carries both axes. Never collapse them into one label.

### Measurement class

- `measured`: produced by a tool during this run.
- `observed`: directly visible in fetched HTML, screenshots, public pages, search results, uploaded raw exports, or inspected files.
- `inferred_risk`: reasoned risk from observed patterns. It is not a measured fact.
- `not_assessed`: unavailable because of missing tool capability, access, private data, blocked public endpoint, or scope limit.

Only `measured` and `observed` can contribute to a score, and only when the metric registry permits scoring.

### Evidence grade

Use E1-E8 from the supplied Pixelkiez design system:

- E1: standardized primary specification or standard.
- E2: platform-official source or official measurement output.
- E3: research-validated.
- E4: reproducible industry measurement or directly reproducible public observation.
- E5: vendor-specific or tool-specific evidence.
- E6: plausible proxy or structured expert observation.
- E7: practitioner heuristic.
- E8: unclear or unvalidated.

E7 and E8 never contribute to the numeric score. E5-E6 contribute only when the registry marks the metric as scoreable and the report explains the limitation.

## Minimum public audit set

Attempt these targets when they exist and are publicly accessible:

1. Homepage.
2. About/profile page.
3. Main service/category page.
4. Representative detail page.
5. Contact/conversion page.
6. Imprint/legal/privacy page where relevant.
7. robots.txt and sitemap.xml.
8. Canonical and language variants.
9. Brand search query.
10. `site:domain` search query where search tooling is available.
11. At least three non-brand intent queries relevant to the visible offer and market.
12. Public performance data when available.

A missing tool or blocked endpoint does not fail the entire audit. Record it as `not_assessed` and reduce coverage.

## Machine-readable measurement mapping

The detailed registry is `assets/measurement-registry.json`; runtime evidence mechanisms are declared in `assets/capability-registry.json`. Every registered metric carries:

- `capability_id`;
- `test_method`;
- `control_basis`;
- `max_evidence_grade`;
- `score_mode`;
- `limitation`;
- category and metric weight.

This implements the auditable chain `metric -> control basis -> test method -> capability -> evidence -> result -> limitation`. A capability record describes what would be needed; it never asserts the runtime actually provides the capability. Unavailable capability means `not_assessed`.

## Audit families

The detailed registry is `assets/measurement-registry.json`. The client report consolidates results into six categories:

1. Auffindbarkeit & SEO.
2. Performance & Technik.
3. Nutzerführung & Conversion.
4. Barrierefreiheit.
5. Vertrauen, Datenschutz & Inhalt.
6. KI-Verständlichkeit.

The internal metric set also covers crawl/indexability, search visibility, internal linking, information architecture, image SEO, media delivery, content freshness, public technology signals, entity clarity, answerability, and consistency.

## Performance hierarchy

Use this order:

1. Real-user field data such as current public field measurements when available.
2. Controlled lab measurement.
3. Local/public technical inspection.
4. Risk model only when stronger evidence is unavailable.

Never state exact LCP, INP, CLS, TTFB, Speed Index, or blocking-time values without a measurement source.

## Search visibility

Keep these separate:

- technically crawlable/indexable;
- apparently indexed in a public search sample;
- visible for sampled non-brand intent;
- business performance from Search Console or Analytics.

Public SERP samples are snapshots, not proof of stable ranking share.

## Internal linking and information architecture

Inspect, where tools allow:

- crawl depth;
- navigation paths;
- descriptive anchor quality;
- contextual links;
- category-to-detail relationships;
- breadcrumbs;
- related-content paths;
- orphan-risk patterns.

Do not claim a complete graph unless the crawl scope proves complete coverage.

## UX and conversion

Use public evidence to judge clarity, not real conversion performance. Typical observations include first-screen clarity, next-step clarity, navigation, readability, form friction, and trust cues.

A UX observation may be scored under the Pixelkiez product rubric when directly observed. Claims about conversion uplift require analytics, user tests, or experiments and remain `SOURCE_NEEDED` otherwise.

## Accessibility

Public checks can identify criterion-level issues or risks. Automated tools and a limited manual sample do not prove WCAG conformance. Record what was tested, what was not tested, and the test population.

## Security and privacy

The public audit may inspect HTTPS, visible privacy/consent surfaces, and high-level headers. It is not a penetration test or legal review. Do not test hidden endpoints, exploit vulnerabilities, or infer legal compliance from surface signals.

## AI readiness

Score machine extractability and answerability only. Keep actual AI citation/visibility separate unless a reproducible sampling method and model/version/time context are recorded. Never present AI visibility as an official search metric.

## Technology snapshot

Public technology observations may identify delivery mode, framework/CMS hints, media handling, JS/CSS risk, redirects, or structured-data architecture. They do not replace repository, dependency, deployment, or backend evidence.

## Prior-audit reconciliation

When earlier audits or tool exports are supplied, use `references/parallel-audit-reconciliation.md`. Preserve current direct evidence over unsupported historical claims. Never merge scores without explaining method differences.

## Impressum legal sidecar
`LEGAL-IMP-01` through `LEGAL-IMP-11` are non-core submetrics. They are absent from `assets/measurement-registry.json` and cannot create Core metric rows. `pixelkiez_score_impact = NONE_DIRECT`. ILES is internal prioritization only.
