#!/usr/bin/env python3
"""Resolve Pixelkiez brand fonts without bundling or redistributing font binaries.

The resolver prefers the requested Schibsted Grotesk / IBM Plex Mono families. It may
use an explicitly approved local fallback for proof/development rendering, but it never
reports that fallback as exact brand parity. Customer release mode must require EXACT.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from fontTools.ttLib import TTFont
except Exception:  # pragma: no cover - capability is reported below
    TTFont = None  # type: ignore

REQUESTED_DISPLAY = "Schibsted Grotesk"
REQUESTED_DATA = "IBM Plex Mono"
APPROVED_DISPLAY_FALLBACKS = ("IBM Plex Sans", "Noto Sans", "DejaVu Sans")
APPROVED_DATA_FALLBACKS = ("Noto Sans Mono", "DejaVu Sans Mono")
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def fc_match(family: str) -> str:
    try:
        proc = subprocess.run(
            ["fc-match", "-f", "%{family}\n", family],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        return proc.stdout.strip().splitlines()[0] if proc.returncode == 0 and proc.stdout.strip() else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def font_names(path: Path) -> set[str]:
    names: set[str] = set()
    if TTFont is None:
        return names
    try:
        font = TTFont(str(path), lazy=True)
        for record in font["name"].names:
            if record.nameID not in {1, 4, 6, 16, 17}:
                continue
            try:
                names.add(record.toUnicode())
            except Exception:
                pass
        font.close()
    except Exception:
        pass
    return names


def candidate_dirs() -> list[Path]:
    values: list[Path] = []
    env = os.environ.get("PIXELKIEZ_FONT_DIR")
    if env:
        values.append(Path(env).expanduser())
    values += [
        Path.home() / ".fonts",
        Path.home() / ".local/share/fonts",
        Path("/usr/local/share/fonts"),
        Path("/usr/share/fonts"),
        Path("/opt/pyvenv/lib/python3.13/site-packages/gradio/templates/frontend/static/fonts"),
        Path("/opt/pyvenv/lib64/python3.13/site-packages/gradio/templates/frontend/static/fonts"),
    ]
    result: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        value = value.resolve()
        if value not in seen and value.exists():
            result.append(value)
            seen.add(value)
    return result


def find_font_file(families: tuple[str, ...]) -> tuple[str | None, Path | None, list[str]]:
    inspected: list[str] = []
    files: list[Path] = []
    for directory in candidate_dirs():
        files.extend(path for path in directory.rglob("*") if path.is_file() and path.suffix.casefold() in FONT_SUFFIXES)

    def style_rank(path: Path) -> tuple[int, str]:
        name = normalized(path.stem)
        if "regular" in name or "book" in name:
            rank = 0
        elif "medium" in name:
            rank = 1
        elif "semibold" in name:
            rank = 2
        elif "bold" in name:
            rank = 3
        else:
            rank = 4
        return rank, str(path)

    for family in families:
        key = normalized(family)
        filename_matches = [path for path in files if key in normalized(path.stem)]
        if filename_matches:
            selected = sorted(filename_matches, key=style_rank)[0]
            return family, selected.resolve(), []
        if TTFont is not None:
            metadata_matches: list[tuple[Path, list[str]]] = []
            for path in files:
                names = sorted(font_names(path))
                if key in normalized(" ".join(names)):
                    metadata_matches.append((path, names))
                if len(inspected) < 20:
                    inspected.append(str(path))
            if metadata_matches:
                selected, names = sorted(metadata_matches, key=lambda item: style_rank(item[0]))[0]
                return family, selected.resolve(), names
    return None, None, inspected


def sibling_style(path: Path | None, family: str | None, style: str) -> Path | None:
    if path is None or not family:
        return None
    key = normalized(family)
    wanted = normalized(style)
    candidates = []
    for candidate in path.parent.rglob("*"):
        if not candidate.is_file() or candidate.suffix.casefold() not in FONT_SUFFIXES:
            continue
        name = normalized(candidate.stem)
        if key in name and wanted in name:
            candidates.append(candidate)
    return sorted(candidates, key=lambda x: str(x))[0].resolve() if candidates else None


def resolve_fonts() -> dict[str, Any]:
    display_exact_family, display_exact_file, _ = find_font_file((REQUESTED_DISPLAY,))
    data_exact_family, data_exact_file, _ = find_font_file((REQUESTED_DATA,))
    display_fallback_family, display_fallback_file, _ = find_font_file(APPROVED_DISPLAY_FALLBACKS)
    data_fallback_family, data_fallback_file, _ = find_font_file(APPROVED_DATA_FALLBACKS)

    display_family = display_exact_family or display_fallback_family or fc_match(APPROVED_DISPLAY_FALLBACKS[0])
    data_family = data_exact_family or data_fallback_family or fc_match(APPROVED_DATA_FALLBACKS[0])
    display_file = display_exact_file or display_fallback_file
    data_file = data_exact_file or data_fallback_file
    display_bold = sibling_style(display_file, display_family, "Bold") or display_file
    data_bold = sibling_style(data_file, data_family, "Bold") or data_file

    exact_display = bool(display_exact_family and display_exact_file)
    exact_data = bool(data_exact_family and data_exact_file)
    if exact_display and exact_data:
        status = "EXACT"
    elif exact_display or exact_data:
        status = "PARTIAL_EXACT_APPROVED_FALLBACK"
    else:
        status = "APPROVED_FALLBACK"
    return {
        "status": status,
        "requested": {"display": REQUESTED_DISPLAY, "data": REQUESTED_DATA},
        "resolved": {
            "display": display_family or "UNKNOWN",
            "data": data_family or "UNKNOWN",
        },
        "exact": {"display": exact_display, "data": exact_data},
        "files": {
            "display_regular": str(display_file) if display_file else None,
            "display_bold": str(display_bold) if display_bold else None,
            "data_regular": str(data_file) if data_file else None,
            "data_bold": str(data_bold) if data_bold else None,
        },
        "fonttools_available": TTFont is not None,
        "font_search_dirs": [str(path) for path in candidate_dirs()],
        "package_policy": "FONT_BINARIES_MUST_NOT_BE_BUNDLED",
        "customer_release_ready": status == "EXACT",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-exact", action="store_true")
    args = parser.parse_args()
    try:
        result = resolve_fonts()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            print(
                f"{result['status']}: display={result['resolved']['display']} "
                f"data={result['resolved']['data']} customer_release_ready={str(result['customer_release_ready']).lower()}"
            )
        if args.require_exact and result["status"] != "EXACT":
            print("FAIL: BRAND_FONT_EXACT_REQUIRED", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
