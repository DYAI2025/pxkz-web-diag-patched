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

The exact Regular and Bold files of both families ship unmodified in `assets/fonts/` under OFL-1.1 and are pinned in `assets/fonts/font-manifest.json` (path, upstream release/commit, SHA-256, git blob, PostScript name, licence). Resolution order:

1. package fonts, verified by manifest hash, name table (family, subfamily, PostScript name), weight, non-variable outlines, required German glyphs and a safe in-tree non-symlink path;
2. `PIXELKIEZ_FONT_DIR`, consulted only when the package fonts are absent, verified by name table, upstream PostScript name, style, weight and glyphs (not hash-pinned);
3. system font directories, same verification;
4. proof-only approved fallback.

A filename or `fc-match` result never proves identity. A present but damaged package manifest blocks `EXACT` for both roles even if a runtime directory holds the fonts. When exact, `@font-face` binds both the Pixelkiez aliases and the real family names to the verified files. After rendering, every embedded font program is identified from its own name/head tables and the outline of every codepoint it carries against the resolved files (`pdf_font_embedding`); any unidentified or non-embedded font, and any glyph drawn as `.notdef`, fails strict mode. `validate_presentation_brand.py` and `finalize_deliverable_manifest.py` re-resolve the fonts live and never take an identity from the receipt. The receipt records `font_provenance` (source, styles, checksums, manifest SHA-256). Font binaries are never copied into customer deliverables.

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

`validate_no_font_binaries.py` enforces the manifest allowlist: every font binary (by suffix or font magic) must be a pinned, verified manifest file inside `assets/fonts/`; unknown or renamed fonts, symlinks, unsafe paths, missing styles and missing or altered licences fail.
