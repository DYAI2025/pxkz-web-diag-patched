#!/usr/bin/env python3
"""Render a Pixelkiez PDF to one PNG per page for mandatory visual QA.

Purpose: produce deterministic page images for agent/human inspection.
Inputs: PDF path and output directory.
Outputs: page-001.png ... page-NNN.png.
Failure: exits non-zero if rendering is unavailable or any page cannot be rendered.
Side effects: writes PNG files only; no network or third-party actions.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def render_with_fitz(pdf: Path, out_dir: Path) -> int:
    try:
        import fitz  # type: ignore
    except Exception:
        return 0
    doc = fitz.open(pdf)
    try:
        for idx, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            pix.save(out_dir / f"page-{idx:03d}.png")
        return len(doc)
    finally:
        doc.close()


def render_with_pdftoppm(pdf: Path, out_dir: Path) -> int:
    exe = shutil.which("pdftoppm")
    if not exe:
        return 0
    prefix = out_dir / "page"
    result = subprocess.run(
        [exe, "-png", "-r", "144", str(pdf), str(prefix)],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "pdftoppm failed")
    raw = sorted(out_dir.glob("page-*.png"))
    for idx, path in enumerate(raw, 1):
        target = out_dir / f"page-{idx:03d}.png"
        if path != target:
            path.rename(target)
    return len(raw)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return fail("usage: render_pdf_pages.py <input.pdf> <output-dir>")
    pdf = Path(argv[1]).resolve()
    out_dir = Path(argv[2]).resolve()
    if not pdf.is_file():
        return fail(f"PDF not found: {pdf}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("page-*.png"):
        old.unlink()
    try:
        count = render_with_fitz(pdf, out_dir)
        if not count:
            count = render_with_pdftoppm(pdf, out_dir)
    except Exception as exc:
        return fail(str(exc))
    if not count:
        return fail("RUNTIME_UNAVAILABLE: no supported PDF rasterizer (PyMuPDF or pdftoppm)")
    print(f"PASS: rendered {count} PDF pages to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
