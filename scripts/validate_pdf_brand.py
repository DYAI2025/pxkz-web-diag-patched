#!/usr/bin/env python3
"""Compatibility entrypoint for the business-first Pixelkiez PDF brand gate."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

def main(argv:list[str])->int:
    if len(argv) not in {4,5}:
        print("FAIL: usage: validate_pdf_brand.py <pdf> <receipt> <brand-tokens.json> [--require-exact-fonts]", file=sys.stderr); return 1
    root=Path(__file__).resolve().parent
    cmd=[sys.executable,str(root/"validate_presentation_brand.py"),*argv[1:]]
    return subprocess.call(cmd)
if __name__=="__main__": raise SystemExit(main(sys.argv))
