#!/usr/bin/env python3
"""Render the Pixelkiez customer presentation with Jinja2 + WeasyPrint and SVG visuals."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import fitz
import weasyprint
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from weasyprint import HTML, default_url_fetcher
from visualization_policy import CUSTOMER_MAX_VISUALS, CUSTOMER_MIN_VISUALS, order_customer_visuals
from check_brand_fonts import resolve_fonts, verify_pdf_font_embedding


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()



def pdf_fonts_and_sizes(pdf: Path) -> tuple[list[str], list[float]]:
    doc = fitz.open(pdf)
    fonts: set[str] = set()
    sizes: list[float] = []
    for page in doc:
        for entry in page.get_fonts(full=True):
            if len(entry) > 3:
                fonts.add(str(entry[3]))
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if isinstance(span.get("size"), (int, float)) and str(span.get("text") or "").strip():
                        sizes.append(float(span["size"]))
    return sorted(fonts), sizes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("output")
    ap.add_argument("--visual-plan", default=None)
    ap.add_argument("--visual-receipt", default=None)
    ap.add_argument("--visual-dir", default=None)
    ap.add_argument("--render-receipt", default=None)
    ap.add_argument("--html-out", default=None)
    ap.add_argument("--require-exact-fonts", action="store_true")
    args = ap.parse_args()
    model_path, output = Path(args.model).resolve(), Path(args.output).resolve()
    root = Path(__file__).resolve().parents[1]
    base = model_path.parent
    plan_path = Path(args.visual_plan).resolve() if args.visual_plan else base / "visualization-plan.json"
    visual_receipt_path = Path(args.visual_receipt).resolve() if args.visual_receipt else base / "visualization-render-receipt.json"
    visual_dir = Path(args.visual_dir).resolve() if args.visual_dir else base / "visuals"
    receipt_path = Path(args.render_receipt).resolve() if args.render_receipt else base / "presentation-render-receipt.json"
    html_path = Path(args.html_out).resolve() if args.html_out else base / "customer_presentation.html"
    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        visual_receipt = json.loads(visual_receipt_path.read_text(encoding="utf-8"))
        if visual_receipt.get("plan_sha256") != sha(plan_path):
            raise ValueError("visual receipt is stale against plan")
        receipt_rows = {(x["id"], x["template_id"]): x for x in visual_receipt.get("visuals", [])}
        visuals = []
        for item in plan.get("visuals", []):
            if item.get("status") != "SELECTED":
                continue
            key = (item["id"], item["template_id"])
            row = receipt_rows.get(key)
            if not row:
                raise ValueError(f"missing visual receipt row: {key}")
            svg_path = (visual_receipt_path.parent / row["svg_path"]).resolve()
            if visual_dir not in svg_path.parents or not svg_path.is_file() or sha(svg_path) != row["svg_sha256"]:
                raise ValueError(f"invalid visual asset: {key}")
            svg = svg_path.read_text(encoding="utf-8")
            if svg.lstrip().startswith("<?xml"):
                svg = svg.split("?>", 1)[1]
            visuals.append({**item, "backend": row["backend"], "svg": svg})
        if len(visuals) < CUSTOMER_MIN_VISUALS:
            raise ValueError(f"customer PDF requires at least {CUSTOMER_MIN_VISUALS} rendered visuals")
        if len(visuals) > CUSTOMER_MAX_VISUALS:
            raise ValueError(f"visualization plan exceeds customer maximum of {CUSTOMER_MAX_VISUALS}; planner must resolve page budget")
        presentation_visuals = order_customer_visuals(visuals)
        omitted_visuals: list[str] = []
        font_resolution = resolve_fonts()
        font_status = str(font_resolution["status"])
        exact = font_status == "EXACT"
        if args.require_exact_fonts and not exact:
            raise ValueError(
                "BRAND_FONT_EXACT_REQUIRED: requested "
                f"{font_resolution['requested']['display']}/{font_resolution['requested']['data']}, resolved "
                f"{font_resolution['resolved']['display']}/{font_resolution['resolved']['data']}"
            )
        css_path = root / "assets/presentation.css"
        template_path = root / "templates/presentation.html.j2"
        css = css_path.read_text(encoding="utf-8")
        files = font_resolution.get("files", {}) if isinstance(font_resolution.get("files"), dict) else {}
        font_faces: list[str] = []
        exact_roles = font_resolution.get("exact", {}) if isinstance(font_resolution.get("exact"), dict) else {}
        for alias, family, role, key, weight in (
            ("PixelkiezDisplay", "Schibsted Grotesk", "display", "display_regular", 400),
            ("PixelkiezDisplay", "Schibsted Grotesk", "display", "display_bold", 700),
            ("PixelkiezData", "IBM Plex Mono", "data", "data_regular", 400),
            ("PixelkiezData", "IBM Plex Mono", "data", "data_bold", 700),
        ):
            value = files.get(key)
            if value:
                path = Path(str(value)).resolve()
                # The real family name is registered only for a verified exact file, so CSS rules and
                # SVG text that name the brand family use the verified file instead of a host lookup.
                for name in (alias, family) if exact_roles.get(role) else (alias,):
                    font_faces.append(
                        f'@font-face {{ font-family: "{name}"; src: url("{path.as_uri()}"); '
                        f'font-style: normal; font-weight: {weight}; }}'
                    )
        css = "\n".join(font_faces) + "\n" + css
        css = css.replace('"Schibsted Grotesk", "DejaVu Sans", sans-serif', '"PixelkiezDisplay", "IBM Plex Sans", "Noto Sans", "DejaVu Sans", sans-serif')
        css = css.replace('"IBM Plex Mono", "DejaVu Sans Mono", monospace', '"PixelkiezData", "IBM Plex Mono", "Noto Sans Mono", "DejaVu Sans Mono", monospace')
        if "http://" in css or "https://" in css or "@import" in css:
            raise ValueError("remote CSS resources are forbidden")
        env = Environment(loader=FileSystemLoader(str(template_path.parent)), undefined=StrictUndefined, autoescape=True)
        template = env.get_template(template_path.name)
        top_ids = plan.get("top_levers", [])
        finding_map = {str(x.get("id")): x for x in model.get("findings", []) if isinstance(x, dict)}
        findings = [finding_map[x] for x in top_ids if x in finding_map]
        if len(findings) != 4:
            raise ValueError("exactly four customer findings required")
        html_text = template.render(model=model, visuals=presentation_visuals, findings=findings, css=css, font_status=font_status)
        if "http://" in html_text or "https://" in html_text:
            # Customer URL text can contain https; resource attributes may not.
            import re
            if re.search(r'(?:src|href)=["\']https?://', html_text, re.I):
                raise ValueError("remote HTML resources are forbidden")
        allowed_roots = {root.resolve(), base.resolve(), visual_dir.resolve()}
        for value in files.values():
            if value:
                allowed_roots.add(Path(str(value)).resolve().parent)
        def local_fetcher(url: str):
            parsed = urlparse(url)
            if parsed.scheme == "data":
                return default_url_fetcher(url)
            if parsed.scheme in {"", "file"}:
                path = Path(unquote(parsed.path)).resolve()
                if not any(path == allowed or allowed in path.parents for allowed in allowed_roots):
                    raise ValueError(f"resource path outside allowlist: {path}")
                return default_url_fetcher(url)
            raise ValueError(f"remote resource scheme forbidden: {parsed.scheme}")
        output.parent.mkdir(parents=True, exist_ok=True)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_text, encoding="utf-8")
        HTML(string=html_text, base_url=str(base), url_fetcher=local_fetcher).write_pdf(str(output))
        doc = fitz.open(output)
        page_count = len(doc)
        doc.close()
        fonts, sizes = pdf_fonts_and_sizes(output)
        embedding = verify_pdf_font_embedding(
            output, font_resolution, {k: v for k, v in files.items() if k in (font_resolution.get("verified_fonts") or {})}
        )
        if args.require_exact_fonts and embedding["status"] != "VERIFIED":
            raise ValueError(
                "BRAND_FONT_EXACT_REQUIRED: embedded PDF fonts do not match the verified brand fonts "
                f"(missing={[k for k, v in embedding['required_embedded'].items() if not v]}, "
                f"unexpected={embedding['unexpected_fonts']}, not_embedded={embedding['not_embedded_fonts']})"
            )
        verified_fonts = font_resolution.get("verified_fonts", {}) if isinstance(font_resolution.get("verified_fonts"), dict) else {}
        receipt = {
            "schema_version": "1.0",
            "status": "PASS",
            "renderer": "WEASYPRINT",
            "renderer_version": getattr(weasyprint, "__version__", "UNKNOWN"),
            "model_sha256": sha(model_path),
            "visualization_plan_sha256": sha(plan_path),
            "visual_render_receipt_sha256": sha(visual_receipt_path),
            "css_sha256": sha(css_path),
            "template_sha256": sha(template_path),
            "html_path": str(html_path.relative_to(receipt_path.parent)),
            "html_sha256": sha(html_path),
            "pdf_sha256": sha(output),
            "page_count": page_count,
            "page_format": "A4",
            "orientation": "landscape",
            "available_visual_count": len(visuals),
            "embedded_visual_count": len(presentation_visuals),
            "omitted_visual_ids": omitted_visuals,
            "brand_font_status": font_status,
            "font_resolution": {
                "requested": font_resolution.get("requested"),
                "resolved": font_resolution.get("resolved"),
                "exact": font_resolution.get("exact"),
                "customer_release_ready": font_resolution.get("customer_release_ready"),
                "font_file_sha256": {
                    key: sha(Path(value)) for key, value in files.items() if value
                },
            },
            "font_provenance": {
                "source": font_resolution.get("source"),
                "package_policy": font_resolution.get("package_policy"),
                "package_fonts_status": (font_resolution.get("package_fonts") or {}).get("status"),
                "package_manifest_sha256": (font_resolution.get("package_fonts") or {}).get("manifest_sha256"),
                "verification": font_resolution.get("verification"),
                "styles": {
                    key: {k: value.get(k) for k in ("family", "style", "weight", "postscript_name", "unique_id", "head_created", "font_revision", "sha256", "source")}
                    for key, value in sorted(verified_fonts.items())
                },
            },
            "pdf_font_embedding": embedding,
            "pdf_fonts": fonts,
            "minimum_rendered_text_size_pt": min(sizes) if sizes else None,
            "body_text_size_pt": 12.0,
            "chart_label_minimum_pt": 10.0,
            "brand_palette": ["#EC5E43", "#0E1414", "#B6C7C4", "#C6D4D1", "#566360", "#FFFFFF"],
            "local_only_resources": True,
            "legacy_reportlab_default": False,
            "limitations": [] if exact and embedding["status"] == "VERIFIED" else [
                f"Exact brand typography is not proven for this PDF (font status {font_status}, "
                f"display {'exact' if exact_roles.get('display') else 'fallback ' + str(font_resolution['resolved']['display'])}, "
                f"data {'exact' if exact_roles.get('data') else 'fallback ' + str(font_resolution['resolved']['data'])}, "
                f"embedding {embedding['status']}). Strict customer release stays blocked until the verified package fonts, "
                "or verified runtime fonts, render both requested families."
            ],
        }
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: WeasyPrint customer PDF pages={page_count} visuals={len(presentation_visuals)}/{len(visuals)} font_status={font_status}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
