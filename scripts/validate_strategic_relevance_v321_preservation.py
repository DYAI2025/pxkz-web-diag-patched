#!/usr/bin/env python3
"""Validate that the Strategic-Relevance patch is a conflict-aware merge on v3.2.1.

The report captures the complete build-controlled v3.2.1 baseline and the exact
allowed modified/added paths. Any unreported deletion, mutation, or addition fails.
Reports/dist/caches are excluded, matching the build digest boundary.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

# Same boundary as pipeline_ledger.digest: whole path components, plus compiled caches.
EXCLUDED_DIRS = {"reports", "dist", "__pycache__", ".git", ".pytest_cache"}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def controlled(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if set(rel.parts) & EXCLUDED_DIRS or path.suffix in {".pyc", ".pyo"}:
            continue
        out[rel.as_posix()] = sha(path)
    return out

def fail(message: str) -> int:
    print("FAIL: " + message, file=sys.stderr)
    return 1

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_strategic_relevance_v321_preservation.py <skill-dir>")
    root = Path(argv[1]).resolve()
    try:
        report = json.loads((root / "reports/strategic-relevance-v321-preservation.json").read_text(encoding="utf-8"))
        if report.get("status") != "PASS":
            raise ValueError("preservation report status is not PASS")
        if report.get("baseline_release") != "3.2.1-measurement-platform-integration":
            raise ValueError("unexpected baseline release")
        if report.get("baseline_tree_digest") != "f9663c8c616f1c6ea1be95098eb6c27065f2018e4f8fe47499059cca93e637f6":
            raise ValueError("unexpected baseline digest")
        baseline = {row["path"]: row["sha256"] for row in report.get("baseline_files", [])}
        modified = {row["path"]: row for row in report.get("modified_files", [])}
        added = {row["path"]: row for row in report.get("added_files", [])}
        deleted = report.get("deleted_files", [])
        if deleted:
            raise ValueError("deletions are not allowed in this merge")
        current = controlled(root)
        errors: list[str] = []
        for rel, old_sha in baseline.items():
            got = current.get(rel)
            if got is None:
                errors.append(f"deleted:{rel}")
                continue
            if rel in modified:
                row = modified[rel]
                if row.get("baseline_sha256") != old_sha or row.get("current_sha256") != got:
                    errors.append(f"modified_hash_mismatch:{rel}")
            elif got != old_sha:
                errors.append(f"unreported_change:{rel}")
        for rel, got in current.items():
            if rel in baseline:
                continue
            row = added.get(rel)
            if not row or row.get("current_sha256") != got:
                errors.append(f"unreported_addition:{rel}")
        for rel in added:
            if rel not in current:
                errors.append(f"missing_added_file:{rel}")
        if set(modified) - set(baseline):
            errors.append("modified list contains non-baseline file")
        if errors:
            raise ValueError(", ".join(errors))
        print(f"PASS: v3.2.1 preservation baseline={len(baseline)} modified={len(modified)} added={len(added)} deleted=0")
        return 0
    except Exception as exc:
        return fail(str(exc))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
