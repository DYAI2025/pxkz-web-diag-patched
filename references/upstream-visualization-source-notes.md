# Upstream Visualization Source Notes

These sources informed the architecture. Repository popularity is not used as authority. Source inspection does not prove performance or production suitability for Pixelkiez.

## Vega-Lite

- repository: `vega/vega-lite`
- inspected snapshot: commit `91eeeb8c2b8a4cf2cf9c1ea238667da0216d7a1c`
- uploaded ZIP SHA-256: `a563cf6cc2b1328620dc05d74fbb90599610486d18037add0d315d142bc56a7e`
- inspected package version: `6.4.3`
- adopted: declarative JSON grammar, schema validation, SVG-oriented static-output architecture and curated template patterns.
- bundled derivative: upstream `build/vega-lite-schema.json`, renamed `assets/vega-lite-schema-v6.4.3.json`, with license notice.
- not claimed: actual Vega runtime execution when the receipt says `PIXELKIEZ_SVG_FALLBACK`.

## WeasyPrint

- repository: `Kozea/WeasyPrint`
- inspected upstream commit: `59283182f277c8fbda95e9ff910180b30a32c60d`
- inspected upstream version: `69.0`; runtime used by this Skill is reported separately by the render receipt.
- adopted: HTML/CSS paged-media rendering, `@font-face`, SVG embedding and PDF generation.
- not bundled: upstream source code.

## Mermaid CLI

- repository: `mermaid-js/mermaid-cli`
- inspected snapshot: commit `6731b15f16819fa8470e4d8403d6c4264d4f0849`
- inspected package version: `11.16.0`
- adopted selectively: optional process/structure diagram backend.
- mandatory fallback: safe local SVG rendering when `mmdc`/Chromium is unavailable.

## fl_chart

- repository: `imaNNeo/fl_chart`
- inspected snapshot: commit `f3a575827312b8f12628b66d12d08066eb4d2570`
- uploaded ZIP SHA-256: `3bc103e99d6b0a511a60be29e0975ba99ecacaf0c7452a805054a45cceb9d01d`
- decision: reference only; no Flutter/Dart runtime added.

## Charts / DGCharts

- repository: `ChartsOrg/Charts`
- inspected snapshot: commit `1bad5469f57628782110b05996d4fa00473abf06`
- uploaded ZIP SHA-256: `3d83481a4ef1e61edb3e80b50cad2996f69877a74667a1b6441661fa942add5a`
- decision: reference only; no Swift/Xcode runtime added.
