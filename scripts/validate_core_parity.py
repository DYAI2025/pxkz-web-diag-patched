#!/usr/bin/env python3
"""Validate core-functionality preservation after customer-story hardening."""
from __future__ import annotations
import json
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_core_parity.py <skill-dir>")
    try:
        report = json.loads((Path(argv[1]) / "reports/core-functionality-preservation.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid core report: {exc}")

    preserved = set(report.get("preserved_core_functions", []))
    required = {
        "website URL intake",
        "detailed client diagnosis",
        "Pixelkiez-branded PDF",
        "customer name in report header",
        "coverage-gated Pixelkiez score and partial-score policy",
        "default 96-field v1.3 five-class ElevenLabs batch CSV export",
        "explicit 96-field v1.2 batch export compatibility",
        "explicit 83-field v1.1 batch export compatibility",
        "legacy 82-field v1 batch export compatibility",
        "customer_email authority and no-invention semantics",
        "13-field ElevenLabs provider compatibility binding with fail-closed sentinels",
        "v1.3 separation of ElevenLabs upload readiness from production prerequisite readiness",
        "v1.3 optional customer_email and defaulted unknown prospect semantics",
    }
    if not required <= preserved:
        return fail("core functions missing: " + ", ".join(sorted(required - preserved)))
    if report.get("unintended_losses"):
        return fail("unintended core losses reported")

    additions = set(report.get("additive_functions", []))
    needed_additions = {
        "deterministic maximum-four customer lever selector",
        "approved v2 visualization planner with four-to-seven evidence-bound customer visuals",
        "low-coverage no-overall-score visual-story fallback",
        "complete analysis_report.json and analysis_report.md projections",
        "WeasyPrint HTML/CSS customer renderer with SVG visuals and receipts",
        "deterministic safe SVG fallback for all approved templates",
        "exact brand-font customer gate with labeled proof fallback",
        "customer plain-language normalization and jargon gate",
        "hard twelve-page default customer PDF limit",
        "customer PDF technical-appendix exclusion while canonical JSON trace remains preserved",
        "low-coverage customer marketing regression eval",
    }
    if not needed_additions <= additions:
        return fail("customer-story additions missing: " + ", ".join(sorted(needed_additions - additions)))

    if report.get("existing_pdf_json_pipeline_changed") is not True:
        return fail("customer PDF pipeline change must be declared intentional")
    note = str(report.get("existing_pdf_json_pipeline_change_note", "")).lower()
    if "regression" not in note or "canonical" not in note:
        return fail("PDF/JSON change note must name canonical-truth preservation and regression evidence")
    evidence = report.get("regression_evidence", [])
    if len(evidence) < 4:
        return fail("regression evidence list is incomplete")
    if report.get("status") != "PASS":
        return fail("core parity status failed")
    print("PASS: core functionality preserved; customer presentation intentionally hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
