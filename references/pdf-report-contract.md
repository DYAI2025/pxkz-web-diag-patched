# Pixelkiez Customer Presentation PDF Contract

## Renderer

The default customer PDF is rendered with Jinja2 HTML/CSS and WeasyPrint. ReportLab is legacy-only and may not silently replace WeasyPrint.

## Page archetype

A4 landscape, normally capped at twelve pages:

1. Cover.
2. Executive summary.
3-9. Four to seven selected visual pages.
10. Four lever cards.
11. Roadmap/recommendation.
12. Measurement boundaries.

The exact count may be lower when coverage legitimately prevents visual selection, but a full audit must meet the four-visual minimum.

## Typography and brand

Read `references/brand-rendering-contract-v2.md`. Core body is 12 pt; chart labels target 10 pt; notes/footer never below 8.5 pt. Use requested Schibsted Grotesk and IBM Plex Mono in customer mode. Font fallback is permitted only in proof mode and must be labeled.

## SVG embedding

Every selected plan visual must have a current render receipt and an SVG digest. Every selected SVG must be embedded exactly once in the presentation. No network-fetched images/fonts/scripts are allowed.

## QA

Structural PDF validation is necessary but insufficient. Render all pages to images. Complete:

- visual QA for readability, clipping, overlap, glyphs, density and every chart page;
- semantic QA against client model and scored audit.

A final bundle passes `--require-customer-release-ready` only after both QA manifests pass and exact fonts are present.
