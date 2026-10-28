#!/usr/bin/env python3
"""Validate and package exactly one Pixelkiez skill folder as skill.zip."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_boundary import never_shipped  # noqa: E402

VALIDATORS = [
    "quick_validate.py", "validate_no_font_binaries.py", "validate_release_gate.py", "validate_pipeline_ledger.py",
]
from check_brand_fonts import FONT_SUFFIXES, looks_like_font_bytes  # noqa: E402


def check_archive_fonts(root: Path, names: list[str], canonical_name: str, heads: dict[str, bytes] | None = None) -> None:
    """The archive must carry each manifest font and licence exactly once and no other font binary."""
    manifest = json.loads((root / "assets/fonts/font-manifest.json").read_text(encoding="utf-8"))
    expected = {entry["path"] for entry in manifest["fonts"]}
    licences = {family["license_file"] for family in manifest["families"]}
    licences |= {notice["path"] for family in manifest["families"] for notice in family.get("notice_files", [])}
    prefix = canonical_name + "/"
    rel = [name[len(prefix):] for name in names if name.startswith(prefix)]
    if len(rel) != len(set(rel)):
        raise SystemExit("FAIL: archive contains duplicate entries")
    heads = heads or {}
    fonts = {name for name in rel if Path(name).suffix.casefold() in FONT_SUFFIXES or looks_like_font_bytes(heads.get(prefix + name, b""))}
    if fonts != expected:
        raise SystemExit(f"FAIL: archive font set differs from manifest: extra={sorted(fonts - expected)} missing={sorted(expected - fonts)}")
    missing = sorted((licences | {"assets/fonts/font-manifest.json"}) - set(rel))
    if missing:
        raise SystemExit("FAIL: archive lacks font licence/manifest files: " + ", ".join(missing))

def packaged_files(root: Path) -> list[str]:
    return [path.relative_to(root).as_posix() for path in sorted(root.rglob("*"))
            if path.is_file() and not never_shipped(path.relative_to(root))]

def write_archive(root: Path, out_dir: Path, canonical_name: str) -> Path:
    archive = out_dir / "skill.zip"
    if out_dir.is_relative_to(root) and (out_dir == root or not never_shipped(out_dir.relative_to(root))):
        raise SystemExit(f"FAIL: output directory {out_dir} lies inside the shipped skill tree; use <skill>/dist or a path outside it")
    out_dir.mkdir(parents=True, exist_ok=True)
    if archive.exists(): archive.unlink()
    files = packaged_files(root)  # listed before the archive exists, so it can never include itself
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for rel in files:
            handle.write(root / rel, Path(canonical_name) / rel)
    return archive

def run_validator(root: Path, name: str) -> None:
    result = subprocess.run([sys.executable, str(root / "scripts" / name), str(root)], text=True, capture_output=True)
    if result.stdout: print(result.stdout.strip())
    if result.returncode:
        if result.stderr: print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir")
    parser.add_argument("out_dir", nargs="?", default="./dist")
    args = parser.parse_args()
    root = Path(args.skill_dir).resolve()
    for name in VALIDATORS: run_validator(root, name)
    evaluation = root / "reports" / "enterprise-skill-evaluation.xml"
    result = subprocess.run([sys.executable, str(root / "scripts" / "validate_enterprise_skill_evaluation.py"), str(evaluation)], text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    canonical_name = skill_text.split("\n---\n", 1)[0].split("name:", 1)[1].splitlines()[0].strip()
    archive = write_archive(root, Path(args.out_dir).resolve(), canonical_name)
    with zipfile.ZipFile(archive) as handle:
        names = handle.namelist()
        roots = {name.split("/", 1)[0] for name in names if "/" in name}
        if roots != {canonical_name} or f"{canonical_name}/SKILL.md" not in names or f"{canonical_name}/agents/openai.yaml" not in names:
            raise SystemExit("FAIL: archive must contain exactly one valid skill folder")
        heads = {name: handle.read(name)[:16] for name in names if not name.endswith("/")}
        check_archive_fonts(root, names, canonical_name, heads)
    print(f"PACKAGED: {archive}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
