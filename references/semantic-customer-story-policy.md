# Semantic Customer Story Policy

## Purpose

This policy controls **how the customer story is authored before rendering**. Final QA is a safety net, not the primary editing step. The default PDF is designed for a business owner who scans pages quickly rather than reading a technical report line by line.

## Core rule: problem in words, evidence in numbers

For every prioritized finding, separate the customer message into four jobs:

1. **Headline** — name the concrete website problem, not the audit category.
2. **Observation** — one short natural-language sentence describing what a visitor or prospect encounters.
3. **Impact** — one short, evidence-bounded explanation of why that matters.
4. **Action** — one concrete next step.

When a direct `measured` or `observed` numeric/ratio signal exists, show it as a **number-first element or decision visual**. Do not hide the number inside a paragraph.

Hard scan-first limits:

- headline: <= 110 characters;
- observation: <= 130 characters;
- impact: <= 135 characters;
- action: <= 125 characters.

These are composition limits, not targets to fill. Shorter is preferred when the meaning stays intact.

The same scan-first discipline applies across the presentation:

- executive takeaway: <= 135 characters;
- each strength/priority: <= 110 characters;
- each category summary: <= 110 characters;
- roadmap action: <= 125 characters;
- recommendation reason: <= 135 characters;
- recommendation next step: <= 125 characters.

Do not truncate with ellipses. If a message does not fit, rewrite it around the single decision-relevant point. Full technical detail stays in canonical JSON and the internal appendix.

## Presentation-mode decision

The client-model builder assigns exactly one mode per prioritized finding:

### `NUMBER_FIRST`

Use when a finding references a direct `measured` or `observed` numeric/ratio value with evidence grade E1-E6.

Examples of suitable signals:

- `3,8 s` loading time;
- `0 von 4` sampled search tests;
- `25 %` directly measured share;
- `12` broken/affected public items when the population is known.

Do **not** manufacture a number from an internal score merely to get a number-first card.

### `EVIDENCE_VISUAL`

Use when there is no suitable direct numeric signal but two or more concrete evidence items can be compared or shown visually.

Typical cases:

- company data differs between two public sources;
- two pages expose contradictory information;
- a finding is best understood by comparing visible evidence rather than explaining it at length.

### `SHORT_TEXT`

Use when the problem is important but genuinely qualitative and no truthful direct number/comparison improves comprehension.

Typical cases:

- mobile next step is unclear;
- keyboard focus is hard to see;
- service wording is ambiguous.

Never invent a chart to avoid text.

## Customer-specificity rule

A prioritized finding must be traceable to the concrete audit through metric refs, evidence refs, source URLs or a direct measured signal. The visible wording must describe a **specific observed problem**, not generic agency language.

Prohibited generic patterns include formulations such as:

- `Hier besteht Optimierungspotenzial.`
- `Dieser Bereich könnte verbessert werden.`
- `Es besteht Handlungsbedarf.`
- `Die Website ist nicht optimal.`
- `Diesen Bereich optimieren.`

The customer should be able to recognize their website situation without needing the company logo to make the statement meaningful.

## Example patterns — guidance, never templates

These examples teach the semantic contrast. **Never copy them into a customer report unless the concrete audit independently supports the exact statement.**

### Auffindbarkeit

Bad prose:

> Im Bereich SEO besteht Optimierungspotenzial bei der Non-Brand-Sichtbarkeit.

Better problem sentence:

> Ihre Leistungen sind ohne Firmennamen für wichtige Suchanfragen schwer auffindbar.

If direct evidence exists, keep the number separate:

> `1 von 3 Suchtests` — Treffer der eigenen Website

### Performance

Bad prose:

> Die mobile Performance könnte verbessert werden und weist ein erhöhtes Optimierungspotenzial auf.

Better problem sentence:

> Der wichtigste Inhalt erscheint mobil spürbar spät.

Number-first signal when measured:

> `3,8 s` — gemessene Ladezeit des wichtigsten sichtbaren Inhalts

### Nutzerführung

Bad prose:

> Die Conversion-Optimierung sollte hinsichtlich der CTA-Hierarchie verbessert werden.

Better problem sentence:

> Auf dem Handy ist nicht sofort klar, was der wichtigste nächste Schritt ist.

No number is required if the finding is qualitative. A short evidence visual is preferable to a decorative score chart when useful.

### Barrierefreiheit

Bad prose:

> Die Accessibility weist Verbesserungspotenzial auf.

Better problem sentence:

> Wer die Seite per Tastatur bedient, sieht nicht immer deutlich, wo er sich befindet.

## Quantitative discipline

A number may be customer-facing only when:

- the metric is `measured` or `observed`;
- evidence grade is E1-E6;
- the value is actually numeric or ratio-shaped;
- the finding references the metric;
- unit/population/scope remain interpretable;
- `does_not_prove` remains respected.

Do not use:

- inferred-risk estimates as measured numbers;
- invented competitor averages;
- unsourced thresholds;
- predicted conversion, revenue or ranking uplift;
- internal scores as a substitute for a real measured value.

## Story selection rule

Do not choose findings because they are easy to visualize. Priority remains:

1. critical/high customer-relevant supported problems;
2. evidence strength and confidence;
3. category diversity;
4. actionability and clarity;
5. visual/numeric suitability only as a tie-breaker.

A major qualitative problem outranks a minor metric simply because the metric is chartable.

## Final rendered-PDF semantic QA

After rendering and visual QA, compare the actual PDF against both `client-report-model.json` and the canonical scored audit.

The inspector must answer all of these positively before PASS:

- **Customer specificity:** Would the page still contain concrete facts about this website if logo/company name were removed?
- **Comprehension:** Can a non-specialist explain the main point in one sentence?
- **Scanability:** Is the main message visible without reading the page like a report chapter?
- **Evidence fidelity:** Does the page say only what the audit supports?
- **Visual-semantic fit:** Does the number/chart actually represent the page claim?
- **Prioritization:** Are the most important concrete customer problems shown rather than generic agency topics?
- **Actionability:** Is the next useful step understandable?
- **Coherence:** Do pages form one consistent story without contradictions or repetition?
- **No metric theatre:** Are charts/numbers used because they improve understanding, not as decoration?

The semantic QA is fail-closed and digest-bound. Creating its manifest leaves it `PENDING`; only actual vision/human inspection may set `PASS`.
