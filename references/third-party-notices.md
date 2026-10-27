# Third-Party Notices

## Bundled Vega-Lite schema

`assets/vega-lite-schema-v6.4.3.json` is taken from the user-supplied `vega/vega-lite` snapshot at commit `91eeeb8c2b8a4cf2cf9c1ea238667da0216d7a1c`. Vega-Lite is licensed under BSD-3-Clause. The corresponding license text is stored at `references/licenses/vega-lite-BSD-3-Clause.txt`.

## Runtime libraries

WeasyPrint, Jinja2 and JSON Schema libraries are runtime dependencies of the executing environment and are not copied into this Skill package. Mermaid CLI and Vega rendering CLIs are optional external capabilities; their availability and actual use are recorded in receipts.

## Not copied

No source code, screenshots or sample designs from Charts/DGCharts or fl_chart are bundled. Their repositories were used only for architecture comparison.

## Fonts

No font binaries are bundled or redistributed. The runtime must supply any requested brand font under its own applicable license and deployment policy.


## Measurement Platform repository snapshots

User-provided snapshots of Open Web Analytics, Statping, CSP Auditor and Web-Check were reviewed as capability references. No application source code from these repositories is copied into this Skill or the companion gateway. The public-probe implementation is an independent small implementation of generic HTTP/TLS/robots/sitemap/header/CSP concepts. `reports/third-party-license-ledger.json` records snapshot digests, observed license evidence and the no-copy decision.
