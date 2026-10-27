#!/usr/bin/env python3
"""Finalize a built deliverable manifest only after completed QA validates.

This script never sets QA to PASS. It consumes already completed digest-bound visual and
semantic QA, reruns their validators, refreshes artifact digests, and derives the final
status. Exact requested brand fonts remain a separate customer-release condition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("FAIL: " + message, file=sys.stderr)
    return 1


def run(args: list[str]) -> None:
    proc = subprocess.run(args, text=True, capture_output=True)
    if proc.returncode:
        raise ValueError((proc.stderr or proc.stdout or "validator failed").strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    root = Path(__file__).resolve().parents[1]
    manifest_path = out / "deliverable-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        visual_qa = json.loads((out / "customer_presentation.visual-qa.json").read_text(encoding="utf-8"))
        semantic_qa = json.loads((out / "customer_presentation.semantic-qa.json").read_text(encoding="utf-8"))
        receipt = json.loads((out / "presentation-render-receipt.json").read_text(encoding="utf-8"))
        run([sys.executable, str(root / "scripts/validate_pdf_visual_qa.py"), str(out / "customer_presentation.pdf"), str(out / "customer_presentation.visual-qa.json")])
        run([sys.executable, str(root / "scripts/validate_customer_semantic_qa.py"), str(out / "customer_presentation.pdf"), str(out / "client-report-model.json"), str(out / "diagnosis-report.json"), str(out / "customer_presentation.semantic-qa.json")])
        run([sys.executable, str(root / "scripts/validate_customer_presentation_quality.py"), str(out), "--json-out", str(out / "customer-presentation-quality-report.json")])
        required = []
        for item in manifest.get("required_artifacts", []):
            if not isinstance(item, dict) or not item.get("path"):
                continue
            path = out / str(item["path"])
            if not path.is_file():
                raise ValueError(f"required artifact missing during finalization: {item['path']}")
            required.append({"path": str(item["path"]), "sha256": sha(path), "bytes": path.stat().st_size})
        manifest["required_artifacts"] = required
        if manifest.get("legal_enabled") is True:
            sidecar = out / "impressum-compliance.json"
            if not sidecar.is_file():
                raise ValueError("legal-enabled finalization missing impressum-compliance.json")
            run([sys.executable, str(root / "scripts/validate_impressum_compliance.py"), str(root), str(sidecar)])
            manifest["impressum_compliance_sha256"] = sha(sidecar)
        visual_status = visual_qa.get("inspection_status")
        semantic_status = semantic_qa.get("inspection_status")
        font_status = receipt.get("brand_font_status")
        qa_complete = visual_status == "PASS" and semantic_status == "PASS"
        quality = json.loads((out / "customer-presentation-quality-report.json").read_text(encoding="utf-8"))
        quality_status = quality.get("quality_status")
        customer_ready = bool(qa_complete and quality_status == "PASS" and font_status == "EXACT")
        manifest.update({
            "status": "CUSTOMER_RELEASE_READY" if customer_ready else ("QA_COMPLETE_FONT_BLOCKED" if qa_complete else "BUILT_PENDING_QA"),
            "qa_status": {"visual": visual_status, "semantic": semantic_status},
            "quality_gate_status": quality_status,
            "customer_release_ready": customer_ready,
            "font_resolution": {
                **(manifest.get("font_resolution") if isinstance(manifest.get("font_resolution"), dict) else {}),
                "status": font_status,
                "customer_release_ready": font_status == "EXACT",
            },
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: deliverable manifest finalized status={manifest['status']} customer_release_ready={str(customer_ready).lower()}")
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
