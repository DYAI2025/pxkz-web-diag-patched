#!/usr/bin/env python3
"""Validate Enterprise Skill Output Evaluator XML reports."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCORE_TAGS = [
    "spec_compliance",
    "research_quality",
    "enterprise_readiness",
    "architecture_quality",
    "release_gate_integrity",
]
DECISIONS = {"PASS", "PASS_WITH_MINOR_REVISIONS", "REVISE", "REBUILD", "BLOCKED"}


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def node_text(node: ET.Element | None) -> str:
    return "" if node is None or node.text is None else node.text.strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_enterprise_skill_evaluation.py <evaluation.xml>")
    path = Path(argv[1])
    if not path.exists():
        return fail(f"file not found: {path}")
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        return fail(f"invalid XML: {exc}")
    if root.tag != "enterprise_skill_evaluation":
        return fail("root tag must be enterprise_skill_evaluation")
    scores = root.find("scores")
    if scores is None:
        return fail("scores missing")
    for tag in SCORE_TAGS:
        if node_text(scores.find(tag)) not in {"1", "2", "3", "4", "5"}:
            return fail(f"score {tag} must be 1-5")
    if node_text(root.find("decision")) not in DECISIONS:
        return fail("invalid decision")
    if not node_text(root.find("reason")):
        return fail("reason missing")
    print("PASS: enterprise skill evaluation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
