# Third-party rendering references

- `vega-lite-schema-v6.4.3.json` is copied from the user-provided `vega-lite-main.zip` snapshot rooted at commit `91eeeb8c2b8a4cf2cf9c1ea238667da0216d7a1c`.
- `vega-lite-LICENSE.txt` is the corresponding BSD-3-Clause license.
- No Vega-Lite runtime bundle, Mermaid runtime, Flutter runtime, Swift runtime is distributed in this Skill. The only third-party font binaries are the four manifest-pinned OFL files in `assets/fonts/` (see `references/third-party-notices.md`).
- Runtime adapters detect locally available `vl-convert`/`vl2svg`/`mmdc`. The deterministic Pixelkiez SVG fallback remains the package-controlled baseline.
