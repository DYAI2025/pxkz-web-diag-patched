#!/usr/bin/env python3
"""Allow only the manifest-pinned Pixelkiez brand fonts as font binaries in the Skill tree.

Compatible entrypoint for the former absolute ban. Every file with a font suffix or a
font-program magic number must be listed in assets/fonts/font-manifest.json, sit inside
assets/fonts/, match its pinned SHA-256 and pass name-table/style/glyph verification.
Missing required styles, missing or altered licence files, unknown font binaries,
symlinks and paths outside the font tree all fail. Fonts hidden in a zip archive, a gzip
stream or a base64 ``data:`` URI are detected too. Fonts embedded inside PDF documents
(for example the hash-pinned template PDF) are document data, not font binaries.
"""
from __future__ import annotations

import base64
import binascii
import gzip
import re
import sys
import zipfile
from pathlib import Path

from check_brand_fonts import FONT_SUFFIXES, PACKAGE_POLICY, looks_like_font, looks_like_font_bytes, verify_packaged_fonts

SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache"}
DATA_URI = re.compile(rb"data:([a-z0-9.+/-]*)(?:;[a-z0-9=.-]+)*;base64,([A-Za-z0-9+/]{16,})", re.IGNORECASE)
FONT_MIME = re.compile(rb"(?:^font/|x-font|font-woff|vnd\.ms-fontobject|opentype|truetype)", re.IGNORECASE)


def hidden_fonts(path: Path) -> list[str]:
    """Font programs inside a zip, a gzip stream or a base64 data: URI of this file."""
    hits: list[str] = []
    try:
        data = path.read_bytes()
    except OSError:
        return hits
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    with archive.open(info) as member:
                        head = member.read(16)
                    if Path(info.filename).suffix.casefold() in FONT_SUFFIXES or looks_like_font_bytes(head):
                        hits.append(f"zip member {info.filename}")
        except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
            hits.append("unreadable zip archive")
    if data[:2] == b"\x1f\x8b":
        try:
            with gzip.open(path) as stream:
                if looks_like_font_bytes(stream.read(16)):
                    hits.append("gzip stream")
        except (OSError, EOFError):
            pass
    for match in DATA_URI.finditer(data):
        try:
            head = base64.b64decode(match.group(2)[:24], validate=True)
        except (binascii.Error, ValueError):
            head = b""
        if FONT_MIME.search(match.group(1)) or looks_like_font_bytes(head):
            hits.append(f"base64 data URI ({match.group(1).decode('ascii', 'replace') or 'no mime'})")
    return hits


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_no_font_binaries.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    package = verify_packaged_fonts(root)
    if package["status"] != "VERIFIED":
        detail = "; ".join(package["issues"]) or "font manifest absent"
        print(f"FAIL: packaged brand fonts not verified ({package['status']}): {detail}", file=sys.stderr)
        return 1
    approved = {Path(value["path"]).resolve() for value in package["fonts"].values()}
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIPPED_DIRS for part in rel.parts):
            continue
        if path.is_symlink():
            if looks_like_font(path) or rel.parts[:2] == ("assets", "fonts"):
                hits.append(f"{rel.as_posix()} (symlink)")
            continue
        if not path.is_file() or path.resolve() in approved:
            continue
        if looks_like_font(path):
            hits.append(rel.as_posix())
        else:
            hits.extend(f"{rel.as_posix()} ({hit})" for hit in hidden_fonts(path))
    if hits:
        print("FAIL: font binaries outside the pinned allowlist: " + ", ".join(hits), file=sys.stderr)
        return 1
    print(
        f"PASS: {PACKAGE_POLICY}: {len(approved)} manifest-pinned font files verified "
        f"(manifest sha256 {package['manifest_sha256']}); no other font binaries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
