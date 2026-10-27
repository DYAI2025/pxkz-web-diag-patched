#!/usr/bin/env python3
"""Digest the customer-semantic control surface used for release evidence binding."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

SEMANTIC_CONTROL_FILES = [
    "SKILL.md",
    "references/semantic-customer-story-policy.md",
    "references/client-storytelling-contract.md",
    "templates/client-report-template.json",
    "schemas/diagnosis-report.schema.json",
    "schemas/client-report.schema.json",
    "scripts/client_story.py",
    "scripts/customer_story_semantics.py",
    "scripts/build_client_report_model.py",
    "scripts/validate_client_report_model.py",
    "scripts/validate_client_semantics.py",
    "scripts/render_diagnosis_pdf.py",
    "scripts/validate_pdf_output.py",
    "scripts/create_customer_semantic_qa_manifest.py",
    "scripts/validate_customer_semantic_qa.py",
    "scripts/run_customer_semantic_evals.py",
    "evals/fixtures/baumdienst-renner-reflection-regression.json",
]


def semantic_bundle_digest(root: Path) -> str:
    h = hashlib.sha256()
    for rel in SEMANTIC_CONTROL_FILES:
        path = root / rel
        if not path.is_file():
            raise ValueError(f"semantic control file missing: {rel}")
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: semantic_release_evidence.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    try:
        print(semantic_bundle_digest(root))
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
