#!/usr/bin/env python3
"""Block bundled font binaries; Pixelkiez fonts must be supplied by the runtime."""
from __future__ import annotations
import sys
from pathlib import Path

FONT_SUFFIXES={'.ttf','.otf','.woff','.woff2','.eot','.pfb','.pfm'}

def main(argv:list[str])->int:
    if len(argv)!=2:
        print('FAIL: usage: validate_no_font_binaries.py <skill-dir>',file=sys.stderr);return 1
    root=Path(argv[1]).resolve()
    hits=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.suffix.casefold() in FONT_SUFFIXES]
    if hits:
        print('FAIL: font binaries must not be bundled: '+', '.join(hits),file=sys.stderr);return 1
    print('PASS: no bundled font binaries; runtime font gate remains explicit')
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
