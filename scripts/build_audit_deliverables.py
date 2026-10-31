#!/usr/bin/env python3
"""Build all Pixelkiez audit deliverables atomically from one canonical scored report."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from check_brand_fonts import looks_like_font
from evidence_method_labels import evidence_method
from customer_execution_release import validate_customer_run,copy_proof


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str]) -> None:
    """Run one deterministic build step with a bounded retry instead of hanging forever."""
    last_timeout: subprocess.TimeoutExpired | None = None
    for attempt in (1, 2):
        try:
            proc = subprocess.run(args, text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            last_timeout = exc
            print(f"WARN: build step timeout attempt={attempt}/2: {' '.join(args)}", file=sys.stderr)
            continue
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.returncode:
            if proc.stderr:
                print(proc.stderr.strip(), file=sys.stderr)
            raise RuntimeError("command failed: " + " ".join(args))
        return
    raise RuntimeError("build step timed out twice: " + " ".join(args)) from last_timeout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scored_report")
    parser.add_argument("output_dir")
    parser.add_argument("--force-svg-fallback", action="store_true")
    parser.add_argument("--require-exact-fonts", action="store_true", help="Legacy alias for --release-mode customer")
    parser.add_argument("--release-mode", choices=["proof", "customer"], default="proof")
    parser.add_argument("--priority-context", default=None, help="Optional customer-story industry/goal context, separate from score")
    parser.add_argument("--priority-catalog", default=None, help="Approved industry-priority catalog")
    parser.add_argument("--priority-catalog-sha256", default=None, help="Exact SHA-256 of external industry catalog")
    parser.add_argument("--priority-allow-synthetic", action="store_true", help="Proof/test mode only: honor synthetic test profiles")
    parser.add_argument("--impressum-compliance", default=None, help="Optional validated internal legal sidecar; if supplied it becomes a strict digest-bound artifact")
    parser.add_argument("--execution-run-dir",default=None,help="Mandatory for customer mode: LIVE v2 run with verified completion receipt")
    args = parser.parse_args()
    src = Path(args.scored_report).resolve()
    destination = Path(args.output_dir).resolve()
    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    require_exact = bool(args.require_exact_fonts or args.release_mode == "customer")
    stage_root: Path | None = None
    try:
        if not src.is_file():
            raise ValueError(f"scored report missing: {src}")
        # CUSTOMER must bind to an actual same-epoch 48-obligation execution before rendering.
        execution_source = Path(args.execution_run_dir).resolve() if args.execution_run_dir else None
        if args.release_mode == "customer" and execution_source is None:
            raise ValueError("CUSTOMER_EXECUTION_COMPLETENESS_RECEIPT_REQUIRED")
        if args.release_mode == "customer":
            validate_customer_run(root,execution_source,src,require_live=True)
        font_proc = subprocess.run([py, str(root / "scripts/check_brand_fonts.py"), str(root), "--json"], text=True, capture_output=True)
        if font_proc.returncode != 0:
            raise ValueError(font_proc.stderr.strip() or "brand font resolution failed")
        font_state = json.loads(font_proc.stdout)
        if require_exact and font_state.get("status") != "EXACT":
            raise ValueError(
                "BRAND_FONT_EXACT_REQUIRED: the packaged brand fonts (assets/fonts/font-manifest.json) or verified "
                "runtime fonts must resolve Schibsted Grotesk and IBM Plex Mono exactly; "
                f"current status={font_state.get('status')} resolved={font_state.get('resolved')} "
                f"package={(font_state.get('package_fonts') or {}).get('status')} "
                f"issues={(font_state.get('package_fonts') or {}).get('issues', [])[:5]}"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        stage_root = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=str(destination.parent)))
        out = stage_root / destination.name
        out.mkdir(parents=True, exist_ok=True)
        canonical = out / "diagnosis-report.json"
        shutil.copy2(src, canonical)
        execution_proof = copy_proof(root,execution_source,out,canonical) if args.release_mode == "customer" else None
        legal_sidecar = None
        legal_projection = None
        if args.impressum_compliance:
            legal_src = Path(args.impressum_compliance).resolve()
            if not legal_src.is_file():
                raise ValueError(f"impressum compliance sidecar missing: {legal_src}")
            legal_sidecar = out / "impressum-compliance.json"
            shutil.copy2(legal_src, legal_sidecar)
            run([py, str(root / "scripts/validate_impressum_compliance.py"), str(root), str(legal_sidecar)])
            legal_projection = out / "legal-customer-projection.json"
            run([py, str(root / "scripts/legal_customer_projection.py"), str(legal_sidecar), str(legal_projection)])
            run([py, str(root / "scripts/validate_impressum_projection.py"), str(legal_sidecar), str(canonical)])
        else:
            # A legal customer risk is admissible only as the validated projection of a supplied sidecar.
            claimed = [str(f.get("id")) for f in json.loads(canonical.read_text(encoding="utf-8")).get("findings", [])
                       if isinstance(f, dict) and isinstance(f.get("customer_risk"), dict) and f["customer_risk"]]
            if claimed:
                raise ValueError("LEGAL_SIDECAR_REQUIRED: customer_risk findings without --impressum-compliance: " + ", ".join(claimed))
        analysis = out / "analysis_report.json"
        markdown = out / "analysis_report.md"
        model = out / "client-report-model.json"
        plan = out / "visualization-plan.json"
        visuals = out / "visuals"
        vreceipt = out / "visualization-render-receipt.json"
        html = out / "customer_presentation.html"
        pdf = out / "customer_presentation.pdf"
        preceipt = out / "presentation-render-receipt.json"

        run([py, str(root / "scripts/validate_report_input.py"), str(canonical)])
        run([py, str(root / "scripts/validate_measurement_enrichment.py"), str(canonical)])
        run([py, str(root / "scripts/build_internal_analysis_report.py"), str(canonical), str(analysis)])
        run([py, str(root / "scripts/render_internal_analysis_markdown.py"), str(analysis), str(markdown)])
        run([py, str(root / "scripts/validate_internal_analysis_report.py"), str(analysis), str(canonical), str(markdown)])
        run([py, str(root / "scripts/validate_analysis_report_completeness.py"), str(analysis), str(markdown), str(canonical)])
        # Plan and model must receive identical priority inputs so the PDF shows one lever selection.
        priority_args: list[str] = []
        if args.priority_context:
            priority_args.extend(["--priority-context", str(Path(args.priority_context).resolve())])
            if args.priority_catalog:
                priority_args.extend(["--priority-catalog", str(Path(args.priority_catalog).resolve())])
                if args.priority_catalog_sha256:
                    priority_args.extend(["--priority-catalog-sha256", args.priority_catalog_sha256])
            if args.priority_allow_synthetic:
                if require_exact:
                    raise ValueError("synthetic priority profiles are test data and cannot shape a customer release")
                priority_args.append("--priority-allow-synthetic")
        elif args.priority_catalog:
            raise ValueError("industry catalog without a priority context cannot be applied")
        run([py, str(root / "scripts/build_visualization_plan.py"), str(canonical), str(plan), *priority_args])
        run([py, str(root / "scripts/validate_visualization_plan.py"), str(plan), str(canonical)])
        if args.release_mode == "customer":
            # Example/fixture data stays recognizable: it may appear in proof bundles, never in a customer release.
            # Checked per plotted visual and per metric behind it, so a rubric matrix of fixture metrics is caught too.
            source_metrics = {str(m.get("id")): m for m in json.loads(canonical.read_text(encoding="utf-8")).get("metrics", [])
                              if isinstance(m, dict)}
            synthetic = [str(v.get("template_id")) for v in json.loads(plan.read_text(encoding="utf-8")).get("visuals", [])
                         if isinstance(v, dict) and v.get("status") == "SELECTED"
                         and (v.get("evidence_method") == "SYNTHETIC"
                              or any(evidence_method(source_metrics[r]) == "SYNTHETIC" for r in v.get("metric_refs", []) if r in source_metrics))]
            # Enrichment replayed from a fixture bundle can also reach customer text (highlights), not only charts.
            enrichment = json.loads(canonical.read_text(encoding="utf-8")).get("measurement_enrichment") or {}
            if isinstance(enrichment, dict) and (str(enrichment.get("mode") or "").upper() in {"FIXTURE", "SYNTHETIC"}
                                                 or any(isinstance(m, dict) and evidence_method(m) == "SYNTHETIC"
                                                        for m in enrichment.get("metrics", []))):
                synthetic.append("MEASUREMENT_ENRICHMENT")
            if synthetic:
                raise ValueError("CUSTOMER_RELEASE_BLOCKED: SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT " + ",".join(synthetic))
        claim_bindings = out / "customer-claim-bindings.json"
        customer_cmd = [py, str(root / "scripts/build_client_report_model.py"), str(canonical), str(model), "--visual-plan", str(plan),
                        "--claim-bindings-out", str(claim_bindings), *priority_args]
        if args.priority_context:
            customer_cmd.extend(["--priority-decision-out", str(out / "prioritization-decision.json")])
        run(customer_cmd)
        run([py, str(root / "scripts/validate_client_report_model.py"), str(model)])
        run([py, str(root / "scripts/validate_customer_claim_bindings.py"), str(canonical), str(model), str(claim_bindings)])
        # One reading per metric and one execution order across strengths, matrices, bars, levers and roadmap.
        run([py, str(root / "scripts/validate_customer_surface_consistency.py"), str(canonical), str(plan), str(model), str(claim_bindings)])
        if legal_sidecar is not None:
            run([py, str(root / "scripts/validate_impressum_projection.py"), str(legal_sidecar), str(canonical), str(model)])
        run([py, str(root / "scripts/validate_client_semantics.py"), str(model)])
        run([py, str(root / "scripts/validate_customer_business_language.py"), str(model)])
        command = [py, str(root / "scripts/render_visualizations.py"), str(plan), str(visuals), "--receipt", str(vreceipt)]
        if args.force_svg_fallback:
            command.append("--force-fallback")
        run(command)
        run([py, str(root / "scripts/validate_visualization_assets.py"), str(plan), str(vreceipt), str(visuals)])
        command = [
            py, str(root / "scripts/render_diagnosis_pdf.py"), str(model), str(pdf),
            "--visual-plan", str(plan), "--visual-receipt", str(vreceipt), "--visual-dir", str(visuals),
            "--render-receipt", str(preceipt), "--html-out", str(html),
        ]
        if require_exact:
            command.append("--require-exact-fonts")
        run(command)
        run([py, str(root / "scripts/validate_pdf_output.py"), str(pdf), str(model)])
        if legal_sidecar is not None:
            run([py, str(root / "scripts/validate_impressum_projection.py"), str(legal_sidecar), str(canonical), str(model), str(pdf)])
        run([py, str(root / "scripts/validate_customer_business_language.py"), str(model), str(pdf)])
        run([py, str(root / "scripts/validate_customer_output_guardrails.py"), str(model), str(html), str(pdf), str(visuals)])
        brand_command = [py, str(root / "scripts/validate_pdf_brand.py"), str(pdf), str(preceipt), str(root / "assets/brand-tokens.json")]
        if require_exact:
            brand_command.append("--require-exact-fonts")
        run(brand_command)
        pages = out / "rendered-pages"
        run([py, str(root / "scripts/render_pdf_pages.py"), str(pdf), str(pages)])
        visual_qa = out / "customer_presentation.visual-qa.json"
        semantic_qa = out / "customer_presentation.semantic-qa.json"
        run([py, str(root / "scripts/create_pdf_visual_qa_manifest.py"), str(pdf), str(pages), str(visual_qa), "--visualization-plan", str(plan)])
        run([py, str(root / "scripts/create_customer_semantic_qa_manifest.py"), str(pdf), str(model), str(canonical), str(semantic_qa)])
        quality_report = out / "customer-presentation-quality-report.json"
        run([py, str(root / "scripts/validate_customer_presentation_quality.py"), str(out), "--allow-pending", "--json-out", str(quality_report)])

        required = [canonical, analysis, markdown, model, claim_bindings, plan, vreceipt, html, preceipt, pdf, visual_qa, semantic_qa, quality_report]
        if legal_sidecar is not None:
            required.append(legal_sidecar)
        if legal_projection is not None:
            required.append(legal_projection)
        manifest = {
            "schema_version": "1.0",
            "status": "BUILT_PENDING_QA",
            "release_mode": args.release_mode,
            "source_input_sha256": sha(src),
            "source_report_sha256": sha(canonical),
            "execution_proof": execution_proof,
            "required_artifacts": [
                {"path": str(path.relative_to(out)), "sha256": sha(path), "bytes": path.stat().st_size}
                for path in required
            ],
            "visual_files": [
                {"path": str(path.relative_to(out)), "sha256": sha(path)} for path in sorted(visuals.glob("*.svg"))
            ],
            "font_resolution": {
                "status": font_state.get("status"),
                "requested": font_state.get("requested"),
                "resolved": font_state.get("resolved"),
                "customer_release_ready": font_state.get("customer_release_ready"),
                "source": font_state.get("source"),
                "package_fonts_status": (font_state.get("package_fonts") or {}).get("status"),
                "package_manifest_sha256": (font_state.get("package_fonts") or {}).get("manifest_sha256"),
            },
            "qa_status": {"visual": "PENDING_ACTUAL_INSPECTION", "semantic": "PENDING_ACTUAL_INSPECTION"},
            "quality_gate_status": "PENDING_QA",
            "customer_release_ready": False,
            "legal_enabled": legal_sidecar is not None,
            "impressum_compliance_sha256": sha(legal_sidecar) if legal_sidecar is not None else None,
            "legal_customer_projection_sha256": sha(legal_projection) if legal_projection is not None else None,
            "does_not_prove": [
                "customer approval",
                "commercial outcome",
                "exact production font parity when font status is not EXACT",
                "live provider or telephony behavior",
            ],
        }
        # Font binaries ship in the Skill package only; customers get the subsets embedded in the PDF.
        font_files = sorted(str(path.relative_to(out)) for path in out.rglob("*") if path.is_file() and looks_like_font(path))
        if font_files:
            raise ValueError("font binaries must not be copied into customer deliverables: " + ", ".join(font_files))
        (out / "deliverable-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run([
            py, str(root / "scripts/validate_deliverable_bundle.py"), str(out),
            "--json-out", str(out / "deliverable-bundle-validation.json"),
        ])

        if destination.exists():
            shutil.rmtree(destination)
        os.replace(out, destination)
        shutil.rmtree(stage_root, ignore_errors=True)
        stage_root = None
        print(
            f"PASS: deliverable suite built atomically visuals={len(manifest['visual_files'])} "
            f"status=BUILT_PENDING_QA font={font_state.get('status')}"
        )
        return 0
    except Exception as exc:
        if stage_root is not None:
            shutil.rmtree(stage_root, ignore_errors=True)
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
