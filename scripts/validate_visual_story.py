#!/usr/bin/env python3
"""Validate the customer-facing Pixelkiez visual story and marketing-output boundaries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from client_story import validate_story_model


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_visual_story.py <client-report-model.json>")
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(str(exc))
    errors = validate_story_model(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"PASS: customer visual story ({len(data.get('visualizations', []))} charts, "
        f"{len(data.get('findings', []))} levers, technical appendix excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
