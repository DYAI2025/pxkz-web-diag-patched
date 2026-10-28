#!/usr/bin/env python3
"""Validate a complete Pixelkiez audit deliverable directory.

Default mode validates deterministic build completeness. `--require-customer-release-ready`
additionally requires exact requested brand fonts and completed visual + semantic QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from check_brand_fonts import looks_like_font


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(args, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def fail(message: str, out: Path | None = None, payload: dict[str, Any] | None = None) -> int:
    if out is not None and payload is not None:
        payload["status"] = "FAIL"
        payload.setdefault("errors", []).append(message)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FAIL: " + message, file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--require-customer-release-ready", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.output_dir).resolve()
    report_path = Path(args.json_out).resolve() if args.json_out else out_dir / "deliverable-bundle-validation.json"
    root = Path(__file__).resolve().parents[1]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "PENDING",
        "output_dir": str(out_dir),
        "customer_release_required": bool(args.require_customer_release_ready),
        "checks": [],
        "errors": [],
    }
    try:
        required = [
            "diagnosis-report.json",
            "analysis_report.json",
            "analysis_report.md",
            "client-report-model.json",
            "visualization-plan.json",
            "visualization-render-receipt.json",
            "customer_presentation.html",
            "customer_presentation.pdf",
            "presentation-render-receipt.json",
            "customer_presentation.visual-qa.json",
            "customer_presentation.semantic-qa.json",
            "customer-presentation-quality-report.json",
            "deliverable-manifest.json",
        ]
        missing = [name for name in required if not (out_dir / name).is_file()]
        if missing:
            return fail("missing required artifacts: " + ", ".join(missing), report_path, payload)
        payload["checks"].append({"id": "required_artifacts", "status": "PASS", "count": len(required)})

        py = sys.executable
        commands = [
            [py, str(root / "scripts/validate_internal_analysis_report.py"), str(out_dir / "analysis_report.json"), str(out_dir / "diagnosis-report.json"), str(out_dir / "analysis_report.md")],
            [py, str(root / "scripts/validate_visualization_plan.py"), str(out_dir / "visualization-plan.json"), str(out_dir / "diagnosis-report.json")],
            [py, str(root / "scripts/validate_visualization_assets.py"), str(out_dir / "visualization-plan.json"), str(out_dir / "visualization-render-receipt.json"), str(out_dir / "visuals")],
            [py, str(root / "scripts/validate_pdf_output.py"), str(out_dir / "customer_presentation.pdf"), str(out_dir / "client-report-model.json")],
            [py, str(root / "scripts/validate_presentation_brand.py"), str(out_dir / "customer_presentation.pdf"), str(out_dir / "presentation-render-receipt.json"), str(root / "assets/brand-tokens.json")]
            + (["--require-exact-fonts"] if args.require_customer_release_ready else []),
        ]
        for command in commands:
            code, stdout, stderr = run(command)
            check = {"id": Path(command[1]).stem, "status": "PASS" if code == 0 else "FAIL", "stdout": stdout.strip(), "stderr": stderr.strip()}
            payload["checks"].append(check)
            if code != 0:
                return fail(f"{check['id']} failed", report_path, payload)

        manifest = json.loads((out_dir / "deliverable-manifest.json").read_text(encoding="utf-8"))
        if manifest.get("legal_enabled") is True:
            sidecar = out_dir / "impressum-compliance.json"
            if not sidecar.is_file():
                return fail("legal-enabled bundle missing impressum-compliance.json", report_path, payload)
            if manifest.get("impressum_compliance_sha256") != sha(sidecar):
                return fail("impressum compliance sidecar digest mismatch", report_path, payload)
            code, stdout, stderr = run([sys.executable, str(root / "scripts/validate_impressum_compliance.py"), str(root), str(sidecar)])
            payload["checks"].append({"id":"impressum_compliance_sidecar","status":"PASS" if code==0 else "FAIL","stdout":stdout.strip(),"stderr":stderr.strip()})
            if code != 0:
                return fail("impressum compliance sidecar validation failed", report_path, payload)
        receipt = json.loads((out_dir / "presentation-render-receipt.json").read_text(encoding="utf-8"))
        plan = json.loads((out_dir / "visualization-plan.json").read_text(encoding="utf-8"))
        vreceipt = json.loads((out_dir / "visualization-render-receipt.json").read_text(encoding="utf-8"))
        visual_qa = json.loads((out_dir / "customer_presentation.visual-qa.json").read_text(encoding="utf-8"))
        semantic_qa = json.loads((out_dir / "customer_presentation.semantic-qa.json").read_text(encoding="utf-8"))
        quality = json.loads((out_dir / "customer-presentation-quality-report.json").read_text(encoding="utf-8"))
        source_digest = sha(out_dir / "diagnosis-report.json")
        if manifest.get("source_report_sha256") != source_digest:
            return fail("deliverable manifest source digest mismatch", report_path, payload)
        if plan.get("source_report_sha256") != source_digest:
            return fail("visualization plan source digest mismatch", report_path, payload)
        if vreceipt.get("plan_sha256") != sha(out_dir / "visualization-plan.json"):
            return fail("visualization receipt plan digest mismatch", report_path, payload)
        if receipt.get("pdf_sha256") != sha(out_dir / "customer_presentation.pdf"):
            return fail("presentation receipt PDF digest mismatch", report_path, payload)
        if receipt.get("html_sha256") != sha(out_dir / "customer_presentation.html"):
            return fail("presentation receipt HTML digest mismatch", report_path, payload)
        payload["checks"].append({"id": "cross_artifact_digests", "status": "PASS"})

        selected = [x for x in plan.get("visuals", []) if isinstance(x, dict) and x.get("status") == "SELECTED"]
        if len(selected) < 4 or vreceipt.get("rendered_count") != len(selected) or receipt.get("embedded_visual_count") != len(selected):
            return fail("selected/rendered/embedded visual counts differ or fall below four", report_path, payload)
        payload["checks"].append({"id": "visual_count_parity", "status": "PASS", "count": len(selected)})

        font_files = sorted(str(path.relative_to(out_dir)) for path in out_dir.rglob("*") if path.is_file() and looks_like_font(path))
        if font_files:
            return fail("font binaries must not be shipped in customer deliverables: " + ", ".join(font_files), report_path, payload)
        payload["checks"].append({"id": "no_font_binaries_in_deliverable", "status": "PASS"})

        font_status = receipt.get("brand_font_status")
        embedding_status = (receipt.get("pdf_font_embedding") or {}).get("status")
        visual_status = visual_qa.get("inspection_status")
        semantic_status = semantic_qa.get("inspection_status")
        quality_status = quality.get("quality_status")
        customer_release_ready = bool(font_status == "EXACT" and embedding_status == "VERIFIED" and visual_status == "PASS" and semantic_status == "PASS" and quality_status == "PASS")
        payload.update({
            "status": "PASS",
            "build_complete": True,
            "customer_release_ready": customer_release_ready,
            "brand_font_status": font_status,
            "pdf_font_embedding_status": embedding_status,
            "visual_qa_status": visual_status,
            "semantic_qa_status": semantic_status,
            "quality_gate_status": quality_status,
            "selected_visual_count": len(selected),
            "source_report_sha256": source_digest,
            "product_artifacts": ["analysis_report.json", "analysis_report.md", "customer_presentation.pdf"],
            "does_not_prove": [
                "external ranking or benchmark data not present in the canonical audit",
                "commercial outcome",
                "customer acceptance",
                "exact brand font parity when brand_font_status is not EXACT",
            ],
        })
        if args.require_customer_release_ready and not customer_release_ready:
            return fail(
                f"CUSTOMER_RELEASE_BLOCKED: font={font_status} visual_qa={visual_status} semantic_qa={semantic_status} quality={quality_status}",
                report_path,
                payload,
            )
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"PASS: deliverable bundle build_complete=true visuals={len(selected)} "
            f"customer_release_ready={str(customer_release_ready).lower()} font={font_status}"
        )
        return 0
    except Exception as exc:
        return fail(str(exc), report_path, payload)


if __name__ == "__main__":
    raise SystemExit(main())
