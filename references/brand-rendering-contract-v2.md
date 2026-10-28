# Pixelkiez Brand Rendering Contract v2

## Authoritative tokens

Machine tokens: `assets/brand-tokens.json` and `assets/brand.json`.

Core palette:

- Orange `#EC5E43`
- Ink `#0E1414`
- Sage `#B6C7C4`
- Raised Sage `#C6D4D1`
- Sage Line `#566360`
- White `#FFFFFF`

The customer presentation uses A4 landscape, 12-column logic, restrained orange, card rotation, numbered mono labels and the Pixelkiez pixel-grid device.

## Typography

Requested families:

- display/body: `Schibsted Grotesk`;
- data/labels: `IBM Plex Mono`.

Font binaries are not included in the Skill package. `PIXELKIEZ_FONT_DIR` may point to an approved runtime font directory. The renderer records file digests but never exports font binaries.

Two modes exist:

- `proof`: an explicitly approved local fallback may be used and must be labeled in the receipt;
- `customer`: both requested families must resolve exactly or rendering fails with `BRAND_FONT_EXACT_REQUIRED`.

An approved fallback is not exact Pixelkiez typeface parity. The current proof fallback preference is IBM Plex Sans, then Noto Sans, then DejaVu Sans. Data fallback uses Noto Sans Mono or DejaVu Sans Mono when IBM Plex Mono is absent.

## Type-size gates

- Cover H1: 36 pt
- Section H2: 28 pt
- Section H3: 22 pt
- Core body: 12 pt
- Chart labels: at least 10 pt target
- Notes/footer: at least 8.5 pt

No auto-shrink below the minimum is allowed. Rewrite or change layout instead.

Documented exception, four-lever page (`.page.levers`, user-approved 2026-10-28): the four lever cards use a fixed
compact tier because all four must fit one page above the footer band at the client-report schema text budgets
(headline 110, observation 130, impact 135, action 125 characters): page H2 22 pt, card headline 13.5 pt, observation
10 pt, impact and action 9.5 pt, label 8.5 pt. The tier is static CSS, not auto-shrink; it never goes below the 8.5 pt
minimum. Before this tier the cards already used 15/11/10.5 pt and overlapped the footer. `validate_pdf_output.py`
fails the PDF when any body text or card reaches the footer band or a lever field is missing from the lever page.

## Validation

`validate_presentation_brand.py` checks:

- WeasyPrint receipt and current digests;
- A4 landscape/page count;
- selected vs embedded visual counts;
- font status and, in strict mode, exact requested families;
- rendered PDF font aliases;
- minimum extracted text size;
- approved palette and local-only resources.

`validate_no_font_binaries.py` blocks accidental font redistribution.
