#!/usr/bin/env python3
"""Run deterministic full fixture: score, reports, visuals, PDF and v1.3 batch adapter."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

OBSERVED_AGENT = [
    "company_name", "company_website", "prospect_name", "prospect_salutation",
    "call_compliance_status", "call_compliance_note", "lead_source", "consultant_name",
    "meeting_description", "offer_process", "website_analysis_report", "agency_name", "verified_finding",
]


def run(args: list[str]) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError("command failed: " + " ".join(args))
    return result.stdout.strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_fixture_eval.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    fixture = root / "evals/fixtures/synthetic-report.json"
    contract_path = root / "contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    try:
        with tempfile.TemporaryDirectory(prefix="pixelkiez-fixture-") as tmp:
            t = Path(tmp)
            scored = t / "scored.json"
            deliverables = t / "deliverables"
            batch = t / "pixelkiez_elevenlabs_batch.csv"
            batch_validation = t / "pixelkiez_elevenlabs_batch.validation.json"
            context = t / "batch_context.json"
            context.write_text(json.dumps({
                "_contract_digest": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                "_contract_version": contract["version"],
                "phone_number": "+493012345678",
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            run([sys.executable, str(root / "scripts/compute_score.py"), str(fixture), str(scored)])
            run([sys.executable, str(root / "scripts/build_audit_deliverables.py"), str(scored), str(deliverables), "--force-svg-fallback"])

            required = [
                "analysis_report.json", "analysis_report.md", "client-report-model.json",
                "visualization-plan.json", "visualization-render-receipt.json",
                "presentation-render-receipt.json", "customer_presentation.pdf", "deliverable-manifest.json",
            ]
            missing = [name for name in required if not (deliverables / name).is_file()]
            if missing:
                raise RuntimeError("full deliverable suite missing: " + ", ".join(missing))
            analysis = json.loads((deliverables / "analysis_report.json").read_text(encoding="utf-8"))
            if len(analysis.get("metrics", [])) != 48:
                raise RuntimeError("internal analysis report must contain all 48 metrics")
            plan = json.loads((deliverables / "visualization-plan.json").read_text(encoding="utf-8"))
            selected = [v for v in plan.get("visuals", []) if v.get("status") == "SELECTED"]
            if len(selected) < 4 or len(plan.get("top_levers", [])) != 4:
                raise RuntimeError("visualization plan must contain at least four visuals and exactly four levers")
            preceipt = json.loads((deliverables / "presentation-render-receipt.json").read_text(encoding="utf-8"))
            if preceipt.get("renderer") != "WEASYPRINT" or preceipt.get("embedded_visual_count", 0) < 4:
                raise RuntimeError("customer PDF must be WeasyPrint chart-led output")
            if preceipt.get("body_text_size_pt", 0) < 12 or preceipt.get("chart_label_minimum_pt", 0) < 10:
                raise RuntimeError("customer presentation typography minimums regressed")
            if any("serif" in str(x).casefold() for x in preceipt.get("pdf_fonts", [])):
                raise RuntimeError("serif font leaked into customer PDF")

            run([sys.executable, str(root / "scripts/build_elevenlabs_batch_csv.py"), str(scored), str(batch), "--batch-context", str(context), "--validation-out", str(batch_validation)])
            run([sys.executable, str(root / "scripts/validate_elevenlabs_batch_csv.py"), str(batch), "--require-elevenlabs-upload-ready"])
            if batch.read_bytes()[:3] != b"\xef\xbb\xbf":
                raise RuntimeError("batch fixture output lacks UTF-8 BOM")
            with batch.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if len(rows) != 1 or len(rows[0]) != 96 or "customer_email" not in rows[0]:
                raise RuntimeError("fixture batch must contain one 96-field v1.3 row")
            if rows[0]["customer_email"] != "":
                raise RuntimeError("unknown customer_email must remain blank")
            missing_provider = [name for name in OBSERVED_AGENT if not rows[0].get(name, "").strip()]
            if missing_provider:
                raise RuntimeError("fixture batch has blank observed-agent runtime variables: " + ", ".join(missing_provider))
            state = json.loads(batch_validation.read_text(encoding="utf-8"))
            if state.get("export_status") != "AUDIT_EXPORT_COMPLETE" or state.get("field_count") != 96 or state.get("contract_version") != "1.3.0":
                raise RuntimeError("fixture batch export state invalid")
            expected_counts = {"INTERNAL_RECORD": 48, "EL_RUNTIME_REQUIRED": 3, "EL_RUNTIME_DEFAULTED": 18, "OPTIONAL": 14, "PRODUCTION_GATE_ONLY": 13}
            if state.get("classification_counts") != expected_counts:
                raise RuntimeError("v1.3 classification counts invalid")
            if state.get("elevenlabs_upload_status") != "EL_UPLOAD_READY" or state.get("batch_status") != "BATCH_READY":
                raise RuntimeError("missing optional/production-only data must not block upload readiness")
            if state.get("production_prerequisite_gate") != "BLOCKED" or not state.get("missing_production_gate_fields"):
                raise RuntimeError("production prerequisite gate must remain separate and fail closed")
            if state.get("live_call_production_status") != "NOT_ASSESSED":
                raise RuntimeError("website audit fixture must not claim live-call readiness")
        print("PASS: full fixture -> 48-metric JSON/Markdown, chart-led 12-page PDF, 96-field v1.3 batch")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
