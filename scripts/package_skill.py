#!/usr/bin/env python3
"""Validate and package exactly one Pixelkiez skill folder as skill.zip."""
from __future__ import annotations
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

VALIDATORS = [
    "quick_validate.py", "validate_release_gate.py", "validate_pipeline_ledger.py",
]
EXCLUDE_PARTS = {"__pycache__", ".git", "dist"}

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
    out_dir = Path(args.out_dir).resolve(); out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / "skill.zip"
    if archive.exists(): archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(root.rglob("*")):
            if path.is_file() and not (set(path.relative_to(root).parts) & EXCLUDE_PARTS):
                handle.write(path, Path(canonical_name) / path.relative_to(root))
    with zipfile.ZipFile(archive) as handle:
        names = handle.namelist()
        roots = {name.split("/", 1)[0] for name in names if "/" in name}
        if roots != {canonical_name} or f"{canonical_name}/SKILL.md" not in names or f"{canonical_name}/agents/openai.yaml" not in names:
            raise SystemExit("FAIL: archive must contain exactly one valid skill folder")
    print(f"PACKAGED: {archive}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
