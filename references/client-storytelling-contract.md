# Pixelkiez Client Storytelling Contract

## Goal

The default customer PDF is a short marketing-facing diagnosis, not a technical audit dump. The canonical `diagnosis-report.json` remains complete and traceable; the PDF contains only the few supported weaknesses, numbers, visualizations and actions that help a website owner understand where improvement is worthwhile.

## Customer-story invariant

A completed default customer PDF must contain:

- at most four prioritized improvement levers;
- four to seven approved chart/diagram pages from the v2 visualization catalog;
- no V12 evidence-table page;
- no technical metric appendix;
- no raw source ledger;
- one short measurement-boundaries page;
- at most twelve pages total.

If the runtime cannot build at least four truthful v2-catalog visualizations from direct or already-approved derived scoring evidence, the customer PDF is not complete. Do not invent data to satisfy the gate.

## One-glance rule

For every decision page, a non-specialist should be able to answer quickly:

1. What did Pixelkiez observe or measure?
2. How large is the difference, share, score or gap?
3. Why does it matter?
4. What is the smallest useful next step?

Use a supported number when it improves understanding. Prefer statements such as `0 von 4 Suchtests`, `3,8 s statt 2,5 s`, `52 von 100` or `25 %` over abstract technical labels.

## Lever selection

`scripts/client_story.py` deterministically selects the customer levers. Priority is:

1. critical/high evidence-backed findings;
2. category diversity among remaining findings;
3. confidence/evidence order;
4. maximum four total.

`not_assessed` is never a customer improvement lever. It may appear only as a short open-measurement item on the final limits page.

## Visual story

The visualization planner must not depend on an agent remembering to construct chart payloads. It uses this order:

1. valid v2-catalog payloads tied to important findings;
2. V04 ranking of already-scored metric gaps when at least four comparable scored metrics exist;
3. V07 category-score orientation for the weakest scored categories;
4. V07 overall-score orientation when the score display gate permits it.

V12 remains supported by the internal chart library and can be used in technical/internal artifacts, but it does not count as a customer chart and is prohibited in the default customer PDF.

Derived score charts must be marked `DERIVED` and explicitly state that score gaps are not revenue, ranking, conversion or lead forecasts.

Never invent:

- missing series points;
- comparison cohorts;
- thresholds;
- market medians;
- conversion uplift;
- revenue uplift;
- ranking gains;
- customer or traffic counts.

## Plain-language rules

Customer-facing copy must use everyday German. Translate or avoid internal/technical vocabulary where a simpler wording exists.

Prefer:

- `Treffer der eigenen Website` instead of `First-Party-Treffer`;
- `Suchtests mit und ohne Firmennamen` instead of `Brand-/Non-Brand-Suchsample`;
- `wichtige Suchanfragen` instead of `Kernintents`;
- `Firmendaten ueberall angleichen` instead of `Stammdaten synchronisieren`;
- `Belege` instead of `Proof Points`;
- `Anfragen oder Abschluesse` instead of `Conversion`;
- `Seitentitel und Hauptueberschriften` instead of `Titles und H1`.

The customer validator must fail when protected jargon remains in client-visible fields.

## Traceability boundary

Full technical trace remains available outside the default customer PDF:

- all metric records in `diagnosis-report.json`;
- the internal `appendix` object in `client-report-model.json`;
- source/method data;
- `not_assessed`, `MISSING` and `SOURCE_NEEDED` records;
- validation and visual-QA sidecars.

Removing these tables from the customer PDF is a presentation decision, not deletion of evidence. The complete internal projections `analysis_report.json` and `analysis_report.md` are mandatory for the same audit digest.

## Positive-impact language

Explain the plausible benefit of a fix qualitatively unless a suitable measurement source exists.

Allowed without outcome data: `Die Leistung wird schneller verstaendlich; Interessenten muessen weniger interpretieren.`

Not allowed without outcome data: `Das erhoeht die Conversion um 18 %.`

## Completion gate

The first rendered PDF is a draft. The customer PDF may be called complete only when:

- `client_story.visual_story_status = PASS`;
- four to seven selected v2-catalog visual payloads validate;
- there are at most four lever findings;
- technical appendices are excluded from the rendered PDF;
- the PDF has at most twelve pages;
- `validate_client_report_model.py`, `validate_visual_story.py` and `validate_pdf_output.py` pass;
- rendered-page visual QA passes for the exact final PDF digest;
- semantic QA passes for that same final PDF/client-model/scored-report digest set;
- `validate_customer_presentation_quality.py` returns `quality_status=PASS`.

## Additive branch-aware selection (VibeCheck03 follow-up)

An operator-authorized, source-backed context may activate an applicable, approved, dated industry profile. This affects only ordering of already admitted levers within the existing severity hierarchy; the four-lever and visual budgets, legal overrides, quality score and source restrictions remain unchanged. With no approved profile, the legacy selection remains exact. Read `references/branch-aware-customer-prioritization.md`.
