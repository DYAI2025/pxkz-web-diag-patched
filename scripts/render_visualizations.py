#!/usr/bin/env python3
"""Render Pixelkiez visualization-plan entries to SVG with truthful backend receipts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svg_chart_renderer import render_svg  # noqa: E402
from vega_spec_builder import build_spec  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capabilities() -> dict[str, Any]:
    return {
        "vl_convert_python": importlib.util.find_spec("vl_convert") is not None,
        "vl2svg_cli": shutil.which("vl2svg"),
        "mmdc_cli": shutil.which("mmdc"),
        "network_install_attempted": False,
    }



def safe_mermaid_label(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"[\[\]{}<>`|]", " ", text)
    text = text.replace('"', "'").replace(";", ",")
    text = " ".join(text.split())[:80].strip()
    return text or "Schritt"


def validate_svg_safety(svg_text: str) -> None:
    try:
        root = ET.fromstring(svg_text)
    except Exception as exc:
        raise ValueError(f"SVG is not well-formed XML: {exc}") from exc
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1].casefold()
        if local in {"script", "foreignobject"}:
            raise ValueError(f"unsafe SVG element: {local}")
        for key, value in element.attrib.items():
            attr = key.rsplit("}", 1)[-1].casefold()
            if attr.startswith("on"):
                raise ValueError(f"unsafe SVG event attribute: {attr}")
            if attr in {"href", "xlink:href"} and value and not str(value).startswith("#"):
                raise ValueError("external SVG references are forbidden")

def external_vega(spec: dict[str, Any], spec_path: Path, caps: dict[str, Any]) -> tuple[str, str] | None:
    if caps["vl_convert_python"]:
        try:
            import vl_convert as vlc  # type: ignore
            result = vlc.vegalite_to_svg(spec)
            return (result.decode("utf-8") if isinstance(result, bytes) else str(result), "VEGA_LITE_VL_CONVERT")
        except Exception:
            pass
    if caps["vl2svg_cli"]:
        try:
            proc = subprocess.run([str(caps["vl2svg_cli"]), str(spec_path)], text=True, capture_output=True, timeout=30)
            if proc.returncode == 0 and "<svg" in proc.stdout:
                return proc.stdout, "VEGA_LITE_CLI"
        except Exception:
            pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("output_dir")
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--force-fallback", action="store_true")
    args = ap.parse_args()
    plan_path, out = Path(args.plan).resolve(), Path(args.output_dir).resolve()
    root = Path(__file__).resolve().parents[1]
    receipt_path = Path(args.receipt).resolve() if args.receipt else out.parent / "visual-render-receipt.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        out.mkdir(parents=True, exist_ok=True)
        specs_dir = out / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        caps = capabilities()
        rows = []
        for visual in plan.get("visuals", []):
            if visual.get("status") != "SELECTED":
                continue
            vid = str(visual["id"])
            tid = str(visual["template_id"])
            if visual.get("engine") == "VEGA_LITE":
                spec = build_spec(root, visual)
                spec_path = specs_dir / f"{vid}-{tid}.vl.json"
                spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                rendered = None if args.force_fallback else external_vega(spec, spec_path, caps)
                if rendered:
                    svg_text, backend = rendered
                else:
                    svg_text, backend = render_svg(visual), "PIXELKIEZ_SVG_FALLBACK"
            else:
                spec_path = specs_dir / f"{vid}-{tid}.mmd"
                nodes = visual.get("data") if isinstance(visual.get("data"), list) else []
                labels = [safe_mermaid_label(x.get("label")) for x in nodes if isinstance(x, dict) and x.get("label")]
                if not labels:
                    labels = ["Befund", "Auswirkung", "Maßnahme", "Prüfung"]
                spec_path.write_text(
                    "flowchart LR\n  " + " --> ".join(f'N{i}["{label}"]' for i, label in enumerate(labels)) + "\n",
                    encoding="utf-8",
                )
                backend = "PIXELKIEZ_SVG_FALLBACK"
                svg_text = render_svg(visual)
                if not args.force_fallback and caps["mmdc_cli"]:
                    target = out / f"{vid}-{tid}.svg"
                    proc = subprocess.run([str(caps["mmdc_cli"]), "-i", str(spec_path), "-o", str(target), "-b", "transparent"], text=True, capture_output=True, timeout=45)
                    if proc.returncode == 0 and target.is_file():
                        svg_text = target.read_text(encoding="utf-8")
                        backend = "MERMAID_CLI"
            validate_svg_safety(svg_text)
            svg_path = out / f"{vid}-{tid}.svg"
            svg_path.write_text(svg_text.rstrip() + "\n", encoding="utf-8")
            if "<svg" not in svg_text or len(svg_text) < 300:
                raise ValueError(f"invalid SVG for {vid}")
            rows.append({
                "id": vid,
                "template_id": tid,
                "backend": backend,
                "spec_path": str(spec_path.relative_to(receipt_path.parent)),
                "spec_sha256": sha(spec_path),
                "svg_path": str(svg_path.relative_to(receipt_path.parent)),
                "svg_sha256": sha(svg_path),
                "status": "PASS",
            })
        receipt = {
            "schema_version": "1.0",
            "status": "PASS" if rows else "FAIL",
            "plan_sha256": sha(plan_path),
            "rendered_count": len(rows),
            "visuals": rows,
            "capabilities": caps,
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not rows:
            raise ValueError("no selected visuals rendered")
        print(f"PASS: rendered visuals={len(rows)} backends={sorted({x['backend'] for x in rows})}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
