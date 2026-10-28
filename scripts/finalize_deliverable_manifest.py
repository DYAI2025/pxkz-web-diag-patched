#!/usr/bin/env python3
"""Finalize a built deliverable manifest only after completed QA validates.

This script never sets QA to PASS. It consumes already completed digest-bound visual and
semantic QA, reruns their validators, refreshes artifact digests, and derives the final
status. Exact requested brand fonts remain a separate customer-release condition.

Fail-closed: a manifest that says CUSTOMER_RELEASE_READY is downgraded before any re-validation starts,
and any validation failure records CUSTOMER_RELEASE_BLOCKED in the manifest instead of leaving an old
READY status on disk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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
    except Exception as exc:
        return fail(f"unreadable deliverable manifest: {exc}")
    previous_status = manifest.get("status")
    if previous_status == "CUSTOMER_RELEASE_READY":
        # A READY status is never carried over: it is re-earned by this run or replaced.
        manifest.update({"status": "BUILT_PENDING_QA", "customer_release_ready": False})
        manifest.setdefault("status_history", []).append(
            {"from": previous_status, "to": "BUILT_PENDING_QA", "reason": "REVALIDATION_STARTED"})
        write_atomic(manifest_path, manifest)
    try:
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
        embedding_status = (receipt.get("pdf_font_embedding") or {}).get("status")
        if font_status == "EXACT" or embedding_status == "VERIFIED":
            # The receipt was written by the renderer and may have been edited since; re-derive the font verdict.
            run([sys.executable, str(root / "scripts/validate_presentation_brand.py"), str(out / "customer_presentation.pdf"),
                 str(out / "presentation-render-receipt.json"), str(root / "assets/brand-tokens.json"), "--require-exact-fonts"])
        customer_ready = bool(qa_complete and quality_status == "PASS" and font_status == "EXACT" and embedding_status == "VERIFIED")
        manifest.update({
            "status": "CUSTOMER_RELEASE_READY" if customer_ready else ("QA_COMPLETE_FONT_BLOCKED" if qa_complete else "BUILT_PENDING_QA"),
            "qa_status": {"visual": visual_status, "semantic": semantic_status},
            "quality_gate_status": quality_status,
            "customer_release_ready": customer_ready,
            "font_resolution": {
                **(manifest.get("font_resolution") if isinstance(manifest.get("font_resolution"), dict) else {}),
                "status": font_status,
                "customer_release_ready": font_status == "EXACT" and embedding_status == "VERIFIED",
                "pdf_font_embedding_status": embedding_status,
            },
        })
        write_atomic(manifest_path, manifest)
        print(f"PASS: deliverable manifest finalized status={manifest['status']} customer_release_ready={str(customer_ready).lower()}")
        return 0
    except Exception as exc:
        manifest.update({"status": "CUSTOMER_RELEASE_BLOCKED", "customer_release_ready": False,
                         "block_reason": f"{type(exc).__name__}: {exc}"[:500]})
        write_atomic(manifest_path, manifest)
        return fail("CUSTOMER_RELEASE_BLOCKED: " + str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
