# Pixelkiez Brand Contract for Audit PDFs

## Source

This contract is derived from the user-provided Pixelkiez Design System snapshot supplied on 2026-08-26. The bundled exact source token excerpts are in `assets/brand/`.

The skill does not claim the brand system is an external design standard. It is a project requirement.

## Core palette

Use these measured brand values consistently:

- Orange: `#EC5E43`.
- Ink: `#0E1414`.
- Sage: `#B6C7C4`.
- Raised sage: `#C6D4D1`.
- White: `#FFFFFF`.

No gradient and no arbitrary fifth brand hue. Status colors may use the supplied green/amber surfaces, while orange remains the primary brand accent.

## Recognition devices

A report should visibly use at least four of the five Pixelkiez recognition devices:

1. Full-bleed band rhythm: sage -> orange -> sage -> ink.
2. Card color rotation: white, sage, orange, ink.
3. 6 x 3 pixel meter.
4. North-east arrow affordance or its drawn equivalent.
5. Uppercase, letter-spaced mono labels with a hairline opener.

## Typography

The requested report families are:

- Schibsted Grotesk for display/body;
- IBM Plex Mono for measured values, axes and labels.

Font binaries are runtime inputs and must not be bundled or returned in the Skill package. Read `references/brand-rendering-contract-v2.md` for exact resolution rules.

Two explicitly different modes exist:

- proof/QA mode may use a named approved local fallback and must record `BRAND_FONT_DEGRADED` or the exact partial status;
- customer release mode requires both requested families and fails closed with `BRAND_FONT_EXACT_REQUIRED` when either is absent.

Never describe DejaVu, Noto Sans or IBM Plex Sans as exact Pixelkiez font parity. If core content does not fit, rewrite/reflow it; do not shrink the type below the contract minimum.

Target sizes for A4 landscape:

- cover H1: at least 36 pt;
- section H2: about 28 pt;
- section H3: about 22 pt;
- core body: at least 12 pt;
- chart labels: at least 10 pt;
- notes/footer: at least 8.5 pt.

## Spacing and grid

Use an 8 px conceptual base scale. The PDF template maps this to a consistent millimetre grid with 12 columns and restrained gutters. Keep generous whitespace and avoid dense full-page tables in the executive portion.

## Voice

- Plain, direct, quietly confident.
- Short declarative sentences.
- Facts first, then consequence.
- No hype, sales superlatives, or emoji.
- German client reports use formal `Sie` when direct address is needed.
- Explain what was not tested.
- Label estimates and inferences.
- Translate technical issues into understandable user, lead, visibility, trust, or operational consequences without inventing money values.

## Report order

Follow the user-provided doctor-style structure:

1. Cover.
2. Executive summary.
3. Category scores.
4. `Was wurde geprüft?` coverage page.
5. Four to seven approved evidence-bound visual pages from the v2 catalog.
6. Prioritized findings.
7. Roadmap.
8. Recommendation.
9. One short measurement-boundaries page.

The default customer PDF is capped at twelve pages and excludes raw metric/source appendices.

## Brand assets

The renderer uses a text wordmark `Pixelkiez` plus `WEB DESIGN BERLIN`. An older user-provided raster logo remains bundled for compatibility, but the default layout does not depend on it.

## Diagram language

The chart-specific visual grammar is defined by the supplied 24-page template in `assets/PXK_web_audit_template.pdf`: orange carries the primary measured series, ink carries comparison, sage carries context/track; numeric labels use mono treatment; status colors fill bars/bands rather than recoloring evidence text. Every chart exposes measurement population and a visible limitation block. These rules override generic chart styling choices.
