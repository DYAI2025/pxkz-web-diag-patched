# Installability and Distribution

The release artifact is exactly `skill.zip`. The archive contains one folder named `pixelkiez-website-diagnosis` with `SKILL.md`, `agents/openai.yaml`, assets, references, schema, scripts, evals, templates, and reports.

The package can be prepared and validated, but it cannot guarantee a client UI button, workspace permission, plan availability, runtime tool set, or third-party acceptance. These are outside skill control.


## Reporting runtime prerequisites

The packaged Skill contains exactly the four manifest-pinned OFL brand font files plus licences (`assets/fonts/`) and no Node/Flutter/Swift runtime; exact-font customer rendering works offline without host fonts or `PIXELKIEZ_FONT_DIR`. Deterministic SVG fallback rendering and the internal JSON/Markdown builders are package-controlled. WeasyPrint, Jinja2, JSON Schema, PDF inspection libraries and fontTools (required to verify font identity; without it strict mode fails closed) are runtime capabilities.

- Proof mode may render with an explicitly labeled approved fallback font.
- Customer release mode fails closed until Schibsted Grotesk and IBM Plex Mono resolve exactly from an approved runtime font directory.
- Optional `vl2svg`, `vl-convert` or `mmdc` availability is recorded; their absence must not produce a chartless PDF because the approved deterministic SVG fallback remains available.
- The package cannot guarantee the ChatGPT UI, provider network, live benchmark data or a customer-release font installation.
