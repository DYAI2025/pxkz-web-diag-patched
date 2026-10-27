#!/usr/bin/env python3
"""Create validated Vega-Lite specifications from approved Pixelkiez templates."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

from check_brand_fonts import resolve_fonts


def load_schema(root: Path) -> dict[str, Any]:
    return json.loads((root / "assets/vega-lite-schema-v6.4.3.json").read_text(encoding="utf-8"))


def template_path(root: Path, template_id: str) -> Path:
    path = root / "templates/visualizations" / f"{template_id}.vl.json"
    if not path.is_file():
        raise ValueError(f"approved Vega-Lite template missing: {template_id}")
    return path


def build_spec(root: Path, visual: dict[str, Any]) -> dict[str, Any]:
    template_id = str(visual["template_id"])
    if visual.get("engine") != "VEGA_LITE":
        raise ValueError(f"not a Vega-Lite visual: {template_id}")
    spec = copy.deepcopy(json.loads(template_path(root, template_id).read_text(encoding="utf-8")))
    spec["data"] = {"values": visual.get("data", [])}
    spec["title"] = {"text": str(visual.get("title") or ""), "subtitle": str(visual.get("subtitle") or ""), "anchor": "start"}
    font_resolution = resolve_fonts()
    display_font = str(font_resolution.get("resolved", {}).get("display") or "Noto Sans")
    data_font = str(font_resolution.get("resolved", {}).get("data") or "Noto Sans Mono")
    config = spec.get("config") if isinstance(spec.get("config"), dict) else {}
    def replace_fonts(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: replace_fonts(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_fonts(item) for item in value]
        if value == "Schibsted Grotesk":
            return display_font
        if value == "IBM Plex Mono":
            return data_font
        return value
    spec["config"] = replace_fonts(config)
    usermeta = spec.setdefault("usermeta", {})
    usermeta.update({
        "visual_id": visual.get("id"),
        "metric_refs": visual.get("metric_refs", []),
        "finding_refs": visual.get("finding_refs", []),
        "evidence_class": visual.get("evidence_class"),
        "population": visual.get("population"),
        "method": visual.get("method"),
        "does_not_prove": visual.get("does_not_prove"),
        "brand_font_status": font_resolution.get("status"),
        "resolved_fonts": font_resolution.get("resolved"),
    })
    # Optional target tick in V01 must not render if the plan has no supported target.
    if template_id == "V01_OVERALL_SCORE":
        values = visual.get("data", [])
        if not values or not isinstance(values[0], dict) or not isinstance(values[0].get("target"), (int, float)):
            layers = spec.get("layer", [])
            spec["layer"] = [x for x in layers if not (isinstance(x, dict) and x.get("mark", {}).get("type") == "tick")]
    errors = list(Draft202012Validator(load_schema(root)).iter_errors(spec))
    if errors:
        err = sorted(errors, key=lambda x: list(x.path))[0]
        raise ValueError(f"Vega-Lite schema error for {template_id}: {err.message}")
    return spec
