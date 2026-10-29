# Third-Party Notices

## Bundled Vega-Lite schema

`assets/vega-lite-schema-v6.4.3.json` is taken from the user-supplied `vega/vega-lite` snapshot at commit `91eeeb8c2b8a4cf2cf9c1ea238667da0216d7a1c`. Vega-Lite is licensed under BSD-3-Clause. The corresponding license text is stored at `references/licenses/vega-lite-BSD-3-Clause.txt`.

## Runtime libraries

WeasyPrint, Jinja2 and JSON Schema libraries are runtime dependencies of the executing environment and are not copied into this Skill package. Mermaid CLI and Vega rendering CLIs are optional external capabilities; their availability and actual use are recorded in receipts.

## Not copied

No source code, screenshots or sample designs from Charts/DGCharts or fl_chart are bundled. Their repositories were used only for architecture comparison.

## Fonts

Four unmodified font files are bundled under the SIL Open Font License 1.1 and pinned in `assets/fonts/font-manifest.json`:

- **Schibsted Grotesk** Regular/Bold — Copyright 2023 The Schibsted-Grotesk Project Authors (https://github.com/schibsted/schibsted-grotesk), release 1.100, commit `d485f61f105e1b3935f4d21dfb4d371359798603`, files `fonts/ttf/SchibstedGrotesk-{Regular,Bold}.ttf`. Licence `assets/fonts/schibsted-grotesk/OFL.txt`, authors `assets/fonts/schibsted-grotesk/AUTHORS.txt`. No Reserved Font Name.
- **IBM Plex Mono** Regular/Bold — Copyright © 2017 IBM Corp. with Reserved Font Name "Plex", release `@ibm/plex-mono@2.5.0`, commit `2f9ba1b25957d958db71a849e85d72e3ecfb845a`, files from the release asset `ibm-plex-mono.zip`. Licence `assets/fonts/ibm-plex-mono/LICENSE.txt`.

The files are redistributed only inside the Skill package together with their licences, are not sold by themselves and are not modified or renamed, so the Reserved Font Name clause is not triggered. Customer PDFs contain embedded subsets (document embedding is permitted by OFL-1.1); font files are never placed in customer deliverables. The hash-pinned design-system template `assets/PXK_web_audit_template.pdf` contains its own embedded IBM Plex Mono and Menlo subsets as document data. No other font binary is bundled; `scripts/validate_no_font_binaries.py` enforces this.


## Measurement Platform repository snapshots

User-provided snapshots of Open Web Analytics, Statping, CSP Auditor and Web-Check were reviewed as capability references. No application source code from these repositories is copied into this Skill or the companion gateway. The public-probe implementation is an independent small implementation of generic HTTP/TLS/robots/sitemap/header/CSP concepts. `reports/third-party-license-ledger.json` records snapshot digests, observed license evidence and the no-copy decision.
