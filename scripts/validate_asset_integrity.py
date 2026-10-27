#!/usr/bin/env python3
"""Validate the bundled Pixelkiez brand contract and token snapshots."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_COLORS = {
    "orange": "#EC5E43",
    "ink": "#0E1414",
    "sage": "#B6C7C4",
    "sage_raised": "#C6D4D1",
    "white": "#FFFFFF",
}
EXPECTED_DEVICES = {
    "full_bleed_band_rhythm",
    "card_color_rotation",
    "six_by_three_pixel_meter",
    "mono_uppercase_labels",
    "arrow_affordance",
}
REQUIRED_SNAPSHOTS = [
    "assets/brand/colors.css",
    "assets/brand/typography.css",
    "assets/brand/spacing.css",
    "assets/brand/document.css",
    "assets/brand/brand-devices.css",
    "assets/brand/report-structure.html",
    "assets/brand/score-bands.html",
    "assets/brand/evidence-classes.html",
    "assets/presentation.css",
    "assets/vega-lite-schema-v6.4.3.json",
    "assets/third-party/vega-lite-LICENSE.txt",
]


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_asset_integrity.py <skill-dir>")
    root = Path(argv[1]).resolve()
    try:
        brand = json.loads((root / "assets/brand.json").read_text(encoding="utf-8"))
        tokens = json.loads((root / "assets/brand-tokens.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid brand configuration: {exc}")

    if brand.get("brand_name") != "Pixelkiez":
        return fail("brand name mismatch")
    if brand.get("brand_source_status") != "USER_PROVIDED_DESIGN_SYSTEM":
        return fail("brand source must remain user-provided")
    colors = brand.get("colors", {})
    for key, value in EXPECTED_COLORS.items():
        if str(colors.get(key, "")).upper() != value:
            return fail(f"brand color {key} mismatch")

    devices = set(brand.get("recognition_devices", []))
    if not EXPECTED_DEVICES <= devices:
        return fail("required Pixelkiez recognition devices missing")
    font_cfg = brand.get("fonts", {})
    if font_cfg.get("binary_status") not in {"NOT_BUNDLED", "RUNTIME_SUPPLIED_NOT_BUNDLED"}:
        return fail("font binaries must remain runtime-supplied and not bundled")
    if font_cfg.get("display_requested") != "Schibsted Grotesk" or font_cfg.get("data_requested") != "IBM Plex Mono":
        return fail("requested Pixelkiez report font families drifted")
    if font_cfg.get("customer_release_requirement") != "EXACT_BOTH_FAMILIES":
        return fail("customer release must require both exact requested font families")
    if brand.get("report_geometry", {}).get("format") != "A4 landscape":
        return fail("client report geometry must be A4 landscape")

    typography = tokens.get("typography", {})
    if typography.get("font_binary_status") not in {"NOT_BUNDLED", "RUNTIME_SUPPLIED_NOT_BUNDLED"}:
        return fail("brand tokens must not imply bundled fonts")
    if typography.get("body_min_pt") != 12 or typography.get("chart_label_min_pt") != 10 or typography.get("note_min_pt") != 8.5:
        return fail("brand type-size minima drifted")
    if tokens.get("token_version") != "3.0.0" or tokens.get("source_resolution") != "USER_PROVIDED_PIXELKIEZ_DESIGN_SYSTEM":
        return fail("brand token snapshot mismatch")
    for rel in REQUIRED_SNAPSHOTS:
        path = root / rel
        if not path.is_file() or path.stat().st_size == 0:
            return fail(f"missing brand snapshot: {rel}")

    print("PASS: Pixelkiez brand contract and snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
