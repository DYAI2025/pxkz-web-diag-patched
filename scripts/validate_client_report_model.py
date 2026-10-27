#!/usr/bin/env python3
"""Validate Pixelkiez customer report model, page-story limits and plain-language copy."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import jsonschema

from chart_contract import validate_visualizations
from client_story import validate_story_model, visible_text
from customer_story_semantics import model_finding_semantic_errors
from validate_customer_business_language import FORBIDDEN as BUSINESS_FORBIDDEN

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA = SKILL_DIR / "schemas" / "client-report.schema.json"
INTERNAL_ENUM = re.compile(r"\b(?:targeted_modernization|needs_action|not_assessed|findability_seo|ux_conversion|ai_readiness)\b")


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_client_report_model.py <client-report-model.json>")
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(data)
    except Exception as exc:
        return fail(f"schema validation failed: {exc}")

    errors: list[str] = []
    errors.extend(validate_visualizations(data.get("visualizations", [])))
    errors.extend(validate_story_model(data))
    semantic = data.get("semantic_story", {}) if isinstance(data.get("semantic_story"), dict) else {}
    if semantic.get("status") != "PASS" or semantic.get("errors"):
        errors.append("semantic_story must PASS")
    for finding in data.get("findings", []):
        if isinstance(finding, dict):
            errors.extend(model_finding_semantic_errors(finding))

    if len(data.get("categories", [])) != 6:
        errors.append("exactly six client categories are required")
    cover = data.get("cover", {})
    status = "NO_SCORE" if cover.get("score") is None else "SCORE"
    if cover.get("score") is None and cover.get("score_label") not in {"", None}:
        errors.append("customer no-score state must not expose a partial/coverage label")
    if cover.get("score") is not None and cover.get("score_label") not in {"Pixelkiez Score", "Pixelkiez Bewertungsstand"}:
        errors.append("customer numeric score must use the resolved Pixelkiez score label")
    if len(data.get("executive", {}).get("strengths", [])) > 3 or len(data.get("executive", {}).get("priorities", [])) > 3:
        errors.append("executive summary exceeds 3 strengths/priorities")

    visible = visible_text(data)
    if INTERNAL_ENUM.search(visible):
        errors.append("internal enum leaked into customer-visible copy")
    if "\U0001f600" in visible or "\U0001f680" in visible:
        errors.append("emoji are not permitted in Pixelkiez customer copy")
    serialized = json.dumps({"cover":data.get("cover"),"executive":data.get("executive"),"categories":data.get("categories"),"findings":[{k:f.get(k) for k in ("headline","observation","impact","action")} for f in data.get("findings",[]) if isinstance(f,dict)],"roadmap":data.get("roadmap"),"recommendation":data.get("recommendation"),"closing":data.get("closing")}, ensure_ascii=False)
    for pattern in BUSINESS_FORBIDDEN:
        if re.search(pattern, serialized, re.I):
            errors.append(f"customer business-language firewall hit: {pattern}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"PASS: client report model ({status}, {len(data.get('findings', []))} levers, "
        f"{len(data.get('visualizations', []))} charts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
