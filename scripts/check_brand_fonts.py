#!/usr/bin/env python3
"""Resolve and verify Pixelkiez brand fonts for offline PDF rendering.

Resolution order per role (display = Schibsted Grotesk, data = IBM Plex Mono):

1. package-local fonts listed in ``assets/fonts/font-manifest.json``;
2. an explicitly configured ``PIXELKIEZ_FONT_DIR``;
3. the existing system font directories;
4. an approved fallback family, for proof rendering only.

A file only counts as an exact brand font when its name table names the requested
family, its subfamily and weight match the required style and it covers the required
glyphs. Package-local files must also match their pinned SHA-256 and sit inside the
package font tree. A filename, an fc-match answer or a CSS alias never proves identity.
A manifest that is present but fails verification blocks EXACT for both roles, so a
damaged package can never be hidden behind a runtime font. Customer release mode must
require EXACT.
"""
from __future__ import annotations

import argparse
import hashlib
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

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = "assets/fonts/font-manifest.json"
FONT_ROOT_REL = "assets/fonts"
PACKAGE_POLICY = "PACKAGE_BUNDLED_MANIFEST_PINNED"
REQUESTED_DISPLAY = "Schibsted Grotesk"
REQUESTED_DATA = "IBM Plex Mono"
REQUESTED = {"display": REQUESTED_DISPLAY, "data": REQUESTED_DATA}
APPROVED_DISPLAY_FALLBACKS = ("IBM Plex Sans", "Noto Sans", "DejaVu Sans")
APPROVED_DATA_FALLBACKS = ("Noto Sans Mono", "DejaVu Sans Mono")
STYLES = (("regular", "Regular", 400), ("bold", "Bold", 700))
# One suffix set for the resolver and the package policy validator.
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2", ".eot", ".pfa", ".pfb", ".pfm", ".afm", ".ttc", ".otc", ".dfont", ".fon", ".fnt"}
RESOLVABLE_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}
FONT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1", b"ttcf", b"wOFF", b"wOF2", b"\x80\x01", b"%!PS-AdobeFont", b"%!FontType1")
# Equal to font-manifest.json required_glyphs (tested); also applied to runtime candidates.
DEFAULT_REQUIRED_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789äöüÄÖÜß€–—„“”‚‘’…§°·×%&@#«»→"
# Runtime candidates must carry the upstream PostScript names; a renamed family name alone is not enough.
EXPECTED_POSTSCRIPT = {
    ("Schibsted Grotesk", "Regular"): "SchibstedGrotesk-Regular",
    ("Schibsted Grotesk", "Bold"): "SchibstedGrotesk-Bold",
    ("IBM Plex Mono", "Regular"): "IBMPlexMono",
    ("IBM Plex Mono", "Bold"): "IBMPlexMono-Bold",
}
IGNORED_FILE_NAMES = {".DS_Store"}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def looks_like_font_bytes(head: bytes) -> bool:
    return any(head.startswith(magic) for magic in FONT_MAGIC)


def looks_like_font(path: Path) -> bool:
    """True for a font suffix or a font-program magic number, whatever the suffix."""
    if path.suffix.casefold() in FONT_SUFFIXES:
        return True
    try:
        with path.open("rb") as handle:
            head = handle.read(16)
    except OSError:
        return False
    return looks_like_font_bytes(head)


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


_IDENTITY_CACHE: dict[tuple[str, int, int], dict[str, Any] | None] = {}


def font_identity(path: Path) -> dict[str, Any] | None:
    """Read family, style, weight and cmap from the font's own tables (cached per file state)."""
    try:
        stat = path.stat()
    except OSError:
        return None
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in _IDENTITY_CACHE:
        _IDENTITY_CACHE[key] = _read_identity(path)
    return _IDENTITY_CACHE[key]


def _read_identity(path: Path) -> dict[str, Any] | None:
    if TTFont is None:
        return None
    try:
        font = TTFont(str(path), lazy=True, fontNumber=0)
        names = font["name"]
        identity = {
            "family": names.getDebugName(16) or names.getDebugName(1) or "",
            "style": names.getDebugName(17) or names.getDebugName(2) or "",
            "postscript_name": names.getDebugName(6) or "",
            "version": names.getDebugName(5) or "",
            "weight": int(font["OS/2"].usWeightClass) if "OS/2" in font else None,
            "fs_type": int(font["OS/2"].fsType) if "OS/2" in font else None,
            "variable": "fvar" in font,
            "codepoints": set((font.getBestCmap() or {}).keys()),
        }
        font.close()
        return identity
    except Exception:
        return None


def identity_issues(identity: dict[str, Any] | None, family: str, style: str, weight: int, glyphs: str) -> list[str]:
    if identity is None:
        return ["FONT_UNREADABLE_OR_FONTTOOLS_UNAVAILABLE"]
    issues: list[str] = []
    if normalized(identity["family"]) != normalized(family):
        issues.append(f"FAMILY_MISMATCH:{identity['family']}")
    if normalized(identity["style"]) != normalized(style):
        issues.append(f"STYLE_MISMATCH:{identity['style']}")
    if identity["weight"] != weight:
        issues.append(f"WEIGHT_MISMATCH:{identity['weight']}")
    if identity["variable"]:
        issues.append("VARIABLE_FONT_NOT_APPROVED")
    # Bits 1/2 set without 3 restrict embedding; WeasyPrint must be allowed to embed.
    fs_type = identity["fs_type"] or 0
    if fs_type & 0x0002 or (fs_type & 0x0200):
        issues.append(f"EMBEDDING_RESTRICTED:fsType={fs_type}")
    missing = sorted({char for char in glyphs if ord(char) not in identity["codepoints"]})
    if missing:
        issues.append("GLYPHS_MISSING:" + "".join(missing))
    return issues


def safe_package_path(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or "\\" in rel:
        return None, f"UNSAFE_PATH:{rel!r}"
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts or candidate.parts[:2] != ("assets", "fonts"):
        return None, f"UNSAFE_PATH:{rel}"
    full = root / candidate
    font_root = (root / FONT_ROOT_REL).resolve()
    probe = full
    while probe != root and probe != probe.parent:
        if probe.is_symlink():
            return None, f"SYMLINK_REJECTED:{rel}"
        probe = probe.parent
    resolved = full.resolve()
    if font_root not in resolved.parents:
        return None, f"PATH_ESCAPES_FONT_ROOT:{rel}"
    if not resolved.is_file():
        return None, f"MISSING_FILE:{rel}"
    return resolved, None


def license_issues(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    issues = []
    if "SIL Open Font License" not in text or "Version 1.1" not in text:
        issues.append(f"LICENSE_NOT_OFL_1_1:{path.name}")
    return issues


def verify_packaged_fonts(root: Path | None = None) -> dict[str, Any]:
    """Verify every manifest entry. ABSENT means no manifest; FAILED blocks EXACT."""
    root = (root or PACKAGE_ROOT).resolve()
    manifest_path = root / MANIFEST_REL
    result: dict[str, Any] = {
        "status": "ABSENT",
        "manifest_path": MANIFEST_REL,
        "manifest_sha256": None,
        "issues": [],
        "fonts": {},
    }
    if not manifest_path.exists() and not (root / FONT_ROOT_REL).exists():
        return result
    issues: list[str] = result["issues"]
    if manifest_path.is_symlink() or not manifest_path.is_file():
        issues.append(f"MANIFEST_MISSING:{MANIFEST_REL}")
        result["status"] = "FAILED"
        return result
    result["manifest_sha256"] = sha256_file(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(f"MANIFEST_INVALID_JSON:{exc}")
        result["status"] = "FAILED"
        return result
    try:
        _verify_manifest_entries(root, manifest_path, manifest, result)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        result["issues"].append(f"MANIFEST_MALFORMED:{type(exc).__name__}:{exc}")
        result["fonts"] = {}
    result["status"] = "FAILED" if result["issues"] else "VERIFIED"
    return result


def _verify_manifest_entries(root: Path, manifest_path: Path, manifest: dict[str, Any], result: dict[str, Any]) -> None:
    issues: list[str] = result["issues"]
    if not isinstance(manifest, dict):
        raise TypeError("manifest root must be an object")
    if manifest.get("policy") != PACKAGE_POLICY or manifest.get("font_root") != FONT_ROOT_REL:
        issues.append("MANIFEST_POLICY_MISMATCH")
    glyphs = str(manifest.get("required_glyphs") or DEFAULT_REQUIRED_GLYPHS)
    for key in ("families", "fonts"):
        if not isinstance(manifest.get(key), list):
            raise TypeError(f"{key} must be a list")
    families = {str(f.get("family")): f for f in manifest["families"] if isinstance(f, dict)}
    approved_paths: set[Path] = {manifest_path.resolve()}
    for role, family_name in REQUESTED.items():
        family = families.get(family_name)
        if family is None or family.get("role") != role:
            issues.append(f"FAMILY_RECORD_MISSING:{family_name}")
            continue
        if family.get("license_id") != "OFL-1.1":
            issues.append(f"LICENSE_ID_NOT_APPROVED:{family_name}")
        notices = [{"path": family.get("license_file"), "sha256": family.get("license_sha256")}]
        if not isinstance(family.get("notice_files", []), list):
            raise TypeError(f"notice_files must be a list: {family_name}")
        notices += [n for n in family.get("notice_files", []) if isinstance(n, dict)]
        for index, notice in enumerate(notices):
            path, problem = safe_package_path(root, notice.get("path"))
            if problem:
                issues.append(("LICENSE_" if index == 0 else "NOTICE_") + problem)
                continue
            approved_paths.add(path)
            if sha256_file(path) != notice.get("sha256"):
                issues.append(f"LICENSE_HASH_MISMATCH:{notice.get('path')}")
            elif index == 0:
                issues.extend(license_issues(path))
        if not str(family.get("copyright") or "").strip():
            issues.append(f"COPYRIGHT_MISSING:{family_name}")
    seen: set[tuple[str, str]] = set()
    for entry in manifest["fonts"]:
        if not isinstance(entry, dict):
            issues.append("FONT_ENTRY_INVALID")
            continue
        role, style, family_name = entry.get("role"), entry.get("style"), entry.get("family")
        key = (str(role), str(style))
        label = f"{role}_{str(style).casefold()}"
        if REQUESTED.get(str(role)) != family_name or style not in {s for _, s, _ in STYLES}:
            issues.append(f"FONT_ENTRY_NOT_REQUIRED:{entry.get('path')}")
            continue
        if key in seen:
            issues.append(f"DUPLICATE_FONT_ENTRY:{label}")
            continue
        seen.add(key)
        if entry.get("modified") is not False:
            issues.append(f"FONT_NOT_DECLARED_UNMODIFIED:{entry.get('path')}")
        path, problem = safe_package_path(root, entry.get("path"))
        if problem:
            issues.append(problem)
            continue
        approved_paths.add(path)
        if path.suffix.casefold() not in RESOLVABLE_SUFFIXES or path.name != entry.get("original_filename"):
            issues.append(f"FILENAME_NOT_ORIGINAL:{entry.get('path')}")
        digest = sha256_file(path)
        if digest != entry.get("sha256"):
            issues.append(f"HASH_MISMATCH:{entry.get('path')}")
        weight = entry.get("weight")
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise ValueError(f"weight must be an integer: {entry.get('path')}")
        identity = font_identity(path)
        problems = identity_issues(identity, str(family_name), str(style), weight, glyphs)
        if identity is not None and identity["postscript_name"] != entry.get("postscript_name"):
            problems.append(f"POSTSCRIPT_NAME_MISMATCH:{identity['postscript_name']}")
        issues.extend(f"{p}:{entry.get('path')}" for p in problems)
        result["fonts"][label] = {
            "family": family_name,
            "style": style,
            "weight": weight,
            "postscript_name": entry.get("postscript_name"),
            "path": str(path),
            "package_path": entry.get("path"),
            "sha256": digest,
            "verified": not problems and digest == entry.get("sha256"),
            **{k: v for k, v in (font_fingerprint(path) or {}).items() if k in ("unique_id", "head_created", "font_revision")},
        }
    for role, family_name in REQUESTED.items():
        for _, style, _ in STYLES:
            if (role, style) not in seen:
                issues.append(f"REQUIRED_STYLE_MISSING:{family_name} {style}")
    font_root = root / FONT_ROOT_REL
    if font_root.is_dir():
        for path in sorted(font_root.rglob("*")):
            if path.is_symlink():
                issues.append(f"SYMLINK_REJECTED:{path.relative_to(root).as_posix()}")
            elif path.is_file() and path.resolve() not in approved_paths and path.name not in IGNORED_FILE_NAMES:
                kind = "UNEXPECTED_FONT_ASSET" if looks_like_font(path) else "UNEXPECTED_FILE"
                issues.append(f"{kind}:{path.relative_to(root).as_posix()}")


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


def runtime_font_files() -> list[tuple[Path, str]]:
    """Font files in directory priority order (PIXELKIEZ_FONT_DIR first)."""
    files: list[tuple[Path, str]] = []
    env = os.environ.get("PIXELKIEZ_FONT_DIR")
    env_dir = Path(env).expanduser().resolve() if env else None
    for directory in candidate_dirs():
        source = "CONFIGURED_FONT_DIR" if directory == env_dir else "SYSTEM_FONT_DIR"
        found = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.casefold() in RESOLVABLE_SUFFIXES)
        files.extend((path.resolve(), source) for path in found)
    return files


def find_runtime_exact(family: str, files: list[tuple[Path, str]], glyphs: str) -> dict[str, dict[str, Any]] | None:
    """Return verified Regular+Bold of one family from the first directory that has both."""
    by_source: dict[tuple[str, Path], dict[str, dict[str, Any]]] = {}
    for path, source in files:
        identity = font_identity(path)
        if identity is None or normalized(identity["family"]) != normalized(family):
            continue
        for label, style, weight in STYLES:
            if identity["postscript_name"] != EXPECTED_POSTSCRIPT[(family, style)]:
                continue
            if not identity_issues(identity, family, style, weight, glyphs):
                group = by_source.setdefault((source, path.parent), {})
                group.setdefault(label, {
                    "family": family,
                    "style": style,
                    "weight": weight,
                    "postscript_name": identity["postscript_name"],
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "verified": True,
                    "source": source,
                    **{k: v for k, v in (font_fingerprint(path) or {}).items() if k in ("unique_id", "head_created", "font_revision")},
                })
    for group in by_source.values():
        if {"regular", "bold"} <= set(group):
            return group
    return None


def find_fallback(families: tuple[str, ...], files: list[tuple[Path, str]]) -> tuple[str | None, dict[str, str]]:
    """Proof-only fallback; filename or name-table match is enough because it is never EXACT."""
    for family in families:
        key = normalized(family)
        matches: list[Path] = []
        for path, _ in files:
            identity = font_identity(path)
            names = normalized(identity["family"]) if identity else ""
            if names == key or key in normalized(path.stem):
                matches.append(path)
        if not matches:
            continue
        styles: dict[str, str] = {}
        for label, style, _ in STYLES:
            wanted = normalized(style)
            exact_style = [
                p for p in matches
                if normalized(p.stem).endswith(wanted) and not re.search(r"(semi|extra|demi|ultra)" + wanted + "$", normalized(p.stem))
            ]
            if exact_style:
                styles[label] = str(sorted(exact_style, key=str)[0])
        if "regular" not in styles:
            styles["regular"] = str(sorted(matches, key=str)[0])
        styles.setdefault("bold", styles["regular"])
        return family, styles
    return None, {}


def resolve_fonts(root: Path | None = None) -> dict[str, Any]:
    root = (root or PACKAGE_ROOT).resolve()
    package = verify_packaged_fonts(root)
    glyphs = DEFAULT_REQUIRED_GLYPHS
    files = runtime_font_files()
    resolved: dict[str, str] = {}
    exact: dict[str, bool] = {}
    source: dict[str, str] = {}
    chosen: dict[str, dict[str, Any]] = {}
    fallback_files: dict[str, str] = {}
    for role, family in REQUESTED.items():
        group: dict[str, dict[str, Any]] | None = None
        if package["status"] == "VERIFIED":
            group = {label: {**package["fonts"][f"{role}_{label}"], "source": "PACKAGED"} for label, _, _ in STYLES}
            source[role] = "PACKAGED"
        elif package["status"] == "ABSENT":
            group = find_runtime_exact(family, files, glyphs)
            if group:
                source[role] = group["regular"]["source"]
        if group:
            resolved[role], exact[role] = family, True
            for label, _, _ in STYLES:
                chosen[f"{role}_{label}"] = group[label]
            continue
        exact[role] = False
        fallbacks = APPROVED_DISPLAY_FALLBACKS if role == "display" else APPROVED_DATA_FALLBACKS
        fallback_family, styles = find_fallback(fallbacks, files)
        resolved[role] = fallback_family or fc_match(fallbacks[0])
        source[role] = "APPROVED_FALLBACK" if fallback_family else "UNRESOLVED"
        for label, value in styles.items():
            fallback_files[f"{role}_{label}"] = value

    if exact["display"] and exact["data"]:
        status = "EXACT"
    elif exact["display"] or exact["data"]:
        status = "PARTIAL_EXACT_APPROVED_FALLBACK"
    else:
        status = "APPROVED_FALLBACK"
    file_map = {key: chosen[key]["path"] if key in chosen else fallback_files.get(key) for key in (
        "display_regular", "display_bold", "data_regular", "data_bold")}
    return {
        "status": status,
        "requested": dict(REQUESTED),
        "resolved": {"display": resolved.get("display") or "UNKNOWN", "data": resolved.get("data") or "UNKNOWN"},
        "exact": exact,
        "source": source,
        "files": file_map,
        "verified_fonts": {
            key: {k: v for k, v in value.items() if k != "path"} for key, value in chosen.items()
        },
        "package_fonts": {k: v for k, v in package.items() if k != "fonts"},
        "verification": "NAME_TABLE_POSTSCRIPT_STYLE_WEIGHT_GLYPHS_PLUS_PACKAGE_SHA256",
        "fonttools_available": TTFont is not None,
        "font_search_dirs": [str(path) for path in candidate_dirs()],
        "package_policy": PACKAGE_POLICY,
        "customer_release_ready": status == "EXACT",
    }


def strip_subset_prefix(name: str) -> str:
    return name.split("+", 1)[1] if re.match(r"^[A-Z]{6}\+", name) else name


def _program_identity(font: Any) -> dict[str, Any]:
    names = font["name"] if "name" in font else None
    get = (lambda i: names.getDebugName(i) or "") if names is not None else (lambda i: "")
    return {
        "family": get(16) or get(1),
        "style": get(17) or get(2),
        "postscript_name": get(6),
        "unique_id": get(3),
        "head_created": int(font["head"].created) if "head" in font else None,
        "font_revision": round(float(font["head"].fontRevision), 5) if "head" in font else None,
    }


def font_fingerprint(path: Path) -> dict[str, Any] | None:
    """Identity fields that survive PDF subsetting (name table + head)."""
    if TTFont is None:
        return None
    try:
        font = TTFont(str(path), lazy=True)
        identity = _program_identity(font)
        font.close()
        return identity
    except Exception:
        return None


def _outlines_match(subset: Any, original_path: Path) -> tuple[bool, int]:
    """Compare the resolved outline of every codepoint in the subset with the pinned original."""
    if "glyf" not in subset:
        return False, 0
    original = TTFont(str(original_path))
    try:
        sub_cmap, orig_cmap = subset.getBestCmap() or {}, original.getBestCmap() or {}
        sub_glyf, orig_glyf = subset["glyf"], original["glyf"]
        compared = 0
        for codepoint in sorted(sub_cmap):
            if codepoint not in orig_cmap:
                return False, compared
            a, b = sub_glyf[sub_cmap[codepoint]], orig_glyf[orig_cmap[codepoint]]
            ca, ea, _ = a.getCoordinates(sub_glyf)
            cb, eb, _ = b.getCoordinates(orig_glyf)
            if list(ca) != list(cb) or list(ea) != list(eb):
                return False, compared
            compared += 1
        return compared > 0, compared
    finally:
        original.close()


def verify_pdf_font_embedding(pdf_path: Path, resolution: dict[str, Any], original_files: dict[str, str] | None = None) -> dict[str, Any]:
    """Identify each embedded font program from its own tables; basefont names are CSS aliases, not proof."""
    import io

    import fitz  # PyMuPDF is a declared PDF dependency

    style_keys = {f"{role}_{label}": (family, style) for role, family in REQUESTED.items() for label, style, _ in STYLES}
    expected = {
        key: value for key, value in (resolution.get("verified_fonts") or {}).items()
        if key in style_keys and isinstance(value, dict) and value.get("postscript_name")
        and normalized(str(value.get("family"))) == normalized(style_keys[key][0])
        and value.get("postscript_name") == EXPECTED_POSTSCRIPT[style_keys[key]]
    }
    originals = {key: Path(value) for key, value in (original_files or {}).items() if value and key in expected}
    notdef: list[str] = []
    records: list[dict[str, Any]] = []
    seen: set[int] = set()
    with fitz.open(pdf_path) as doc:
        for page in doc:
            for span in page.get_texttrace():
                for char in span.get("chars", ()):
                    if char[1] == 0 and not chr(char[0]).isspace():
                        notdef.append(f"p{page.number + 1}:{span.get('font')}:U+{char[0]:04X}")
            for entry in page.get_fonts(full=True):
                xref, basefont = entry[0], str(entry[3])
                if xref in seen:
                    continue
                seen.add(xref)
                record: dict[str, Any] = {"basefont": basefont, "embedded": False, "matches": None, "outline_glyphs_compared": 0}
                try:
                    _, font_ext, _, buffer = doc.extract_font(xref)
                except Exception:
                    font_ext, buffer = "", b""
                record["format"] = font_ext
                if buffer and TTFont is not None:
                    record["embedded"] = True
                    try:
                        program = TTFont(io.BytesIO(buffer))
                        record.update(_program_identity(program))
                        for key, want in expected.items():
                            same = all(record.get(f) == want.get(f) for f in ("postscript_name", "unique_id", "head_created", "font_revision") if want.get(f) is not None)
                            if not same or normalized(str(record.get("family"))) != normalized(str(want.get("family"))):
                                continue
                            if key in originals:
                                ok, compared = _outlines_match(program, originals[key])
                                record["outline_glyphs_compared"] = compared
                                if not ok:
                                    record["outline_mismatch"] = key
                                    continue
                            record["matches"] = key
                            break
                        program.close()
                    except Exception as exc:
                        record["parse_error"] = str(exc)
                elif buffer:
                    record["embedded"] = True
                    record["parse_error"] = "FONTTOOLS_UNAVAILABLE"
                records.append(record)
    matched = {r["matches"] for r in records if r.get("matches")}
    required = {key: key in matched for key in expected}
    unexpected = sorted(
        f"{r['basefont']} ({r.get('postscript_name') or r.get('parse_error') or 'unidentified'})"
        for r in records if r["embedded"] and not r.get("matches")
    )
    not_embedded = sorted(r["basefont"] for r in records if not r["embedded"])
    outline_mismatch = sorted(r["outline_mismatch"] for r in records if r.get("outline_mismatch"))
    exact_expected = resolution.get("status") == "EXACT" and len(expected) == 4
    ok = (exact_expected and len(originals) == 4 and all(required.values())
          and not unexpected and not not_embedded and not notdef)
    return {
        "status": "VERIFIED" if ok else ("NOT_APPLICABLE_NON_EXACT" if not exact_expected else "FAILED"),
        "identity_method": "EMBEDDED_PROGRAM_NAME_TABLE_HEAD_AND_OUTLINES" if len(originals) == 4 else "EMBEDDED_PROGRAM_NAME_TABLE_HEAD",
        "required_embedded": required,
        "embedded_fonts": sorted(records, key=lambda r: r["basefont"]),
        "unexpected_fonts": unexpected,
        "not_embedded_fonts": not_embedded,
        "family_mismatch": outline_mismatch,
        "notdef_glyphs": notdef[:50],
    }


def reverify_receipt_fonts(pdf_path: Path, receipt: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Re-derive the font verdict without trusting any identity the receipt states.

    Resolves the fonts live, requires the live file hashes to equal the receipt's
    font_file_sha256 and checks the PDF against the live identities and pinned files.
    """
    live = resolve_fonts(root)
    claimed = (receipt.get("font_resolution") or {}).get("font_file_sha256") or {}
    issues: list[str] = []
    if receipt.get("brand_font_status") == "EXACT":
        if live["status"] != "EXACT":
            issues.append(f"LIVE_RESOLUTION_NOT_EXACT:{live['status']}")
        live_hashes = {key: value.get("sha256") for key, value in live["verified_fonts"].items()}
        if live_hashes != claimed:
            issues.append("RECEIPT_FONT_HASHES_DIFFER_FROM_LIVE_RESOLUTION")
        if (receipt.get("font_provenance") or {}).get("source") != live["source"]:
            issues.append("RECEIPT_FONT_SOURCE_DIFFERS_FROM_LIVE_RESOLUTION")
        resolution = live if not issues else {"status": "EXACT", "verified_fonts": {}}
    else:
        resolution = {"status": receipt.get("brand_font_status"), "verified_fonts": {}}
    embedding = verify_pdf_font_embedding(pdf_path, resolution, live["files"] if not issues else {})
    if issues and embedding["status"] == "VERIFIED":  # pragma: no cover - empty expectations never verify
        embedding["status"] = "FAILED"
    return {"embedding": embedding, "issues": issues, "live": live}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", default=str(PACKAGE_ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-exact", action="store_true")
    args = parser.parse_args()
    try:
        result = resolve_fonts(Path(args.skill_dir))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            print(
                f"{result['status']}: display={result['resolved']['display']} "
                f"data={result['resolved']['data']} source={result['source']} "
                f"package={result['package_fonts']['status']} "
                f"customer_release_ready={str(result['customer_release_ready']).lower()}"
            )
        if args.require_exact and result["status"] != "EXACT":
            detail = "; ".join(result["package_fonts"]["issues"][:5])
            print("FAIL: BRAND_FONT_EXACT_REQUIRED" + (f" ({detail})" if detail else ""), file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
