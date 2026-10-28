#!/usr/bin/env python3
"""Carry reports/strategic-relevance-v321-preservation.json forward by provenance layers.

Convention of the manifest: baseline hashes never change; each authorized patch updates the current_sha256 of
modified/added rows. This script records two layers mechanically:
  L1  the installed skill (zip) relative to what the manifest last recorded
  L2  the candidate tree relative to the installed skill
Every changed path gets a transition row (previous -> current) under patch_layers. Deletions are refused.

Usage: build_v321_preservation_layers.py <candidate-skill-dir> <installed-skill.zip> <manifest.json>
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

L1 = "INSTALLED_V2_1_LEGAL_CUSTOMER_TRUTH"
L2 = "BRANCH_PRIORITY_VC03_CUSTOMER_RELEASE"


def main(argv: list[str]) -> int:
    cand_root, zip_path, manifest_path = Path(argv[1]).resolve(), Path(argv[2]).resolve(), Path(argv[3]).resolve()
    spec = importlib.util.spec_from_file_location("v321", cand_root / "scripts/validate_strategic_relevance_v321_preservation.py")
    v321 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v321)
    cand = v321.controlled(cand_root)

    zf = zipfile.ZipFile(zip_path)
    inst = {}
    for name in zf.namelist():
        if name.endswith("/") or "/" not in name:
            continue
        rel = Path(name.split("/", 1)[1])
        if set(rel.parts) & v321.EXCLUDED_DIRS or rel.suffix in {".pyc", ".pyo"}:
            continue
        inst[rel.as_posix()] = hashlib.sha256(zf.read(name)).hexdigest()

    report = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = {r["path"]: r["sha256"] for r in report["baseline_files"]}
    modified = {r["path"]: r for r in report["modified_files"]}
    added = {r["path"]: r for r in report["added_files"]}
    recorded = {**base, **{p: r["current_sha256"] for p, r in {**modified, **added}.items()}}

    l1 = [{"path": p, "previous_sha256": recorded.get(p), "current_sha256": inst.get(p)}
          for p in sorted(set(recorded) | set(inst)) if inst.get(p) != recorded.get(p)]
    after_l1 = {**recorded, **inst}
    l2 = [{"path": p, "previous_sha256": after_l1.get(p), "current_sha256": cand.get(p)}
          for p in sorted(set(after_l1) | set(cand)) if cand.get(p) != after_l1.get(p)]
    deleted = [t["path"] for t in l1 + l2 if t["current_sha256"] is None]
    if deleted:
        raise SystemExit("FAIL: deletions are not allowed: " + ", ".join(deleted))

    touched = {t["path"]: [L1] for t in l1}
    for t in l2:
        touched.setdefault(t["path"], []).append(L2)
    for rel, got in cand.items():
        if rel not in touched:
            continue
        tag = " + ".join(touched[rel])
        if rel in base:
            row = modified.setdefault(rel, {"path": rel, "baseline_sha256": base[rel], "reason": ""})
            row["current_sha256"] = got
            row["reason"] = " + ".join(x for x in (row.get("reason"), tag) if x)
        else:
            row = added.setdefault(rel, {"path": rel, "reason": ""})
            row["current_sha256"] = got
            row["reason"] = " + ".join(x for x in (row.get("reason"), tag) if x)
    for rel in [p for p, r in modified.items() if cand.get(p) == base.get(p)]:
        del modified[rel]

    report["modified_files"] = [modified[p] for p in sorted(modified)]
    report["added_files"] = [added[p] for p in sorted(added)]
    report["modified_file_count"] = len(modified)
    report["summary"]["current_modified"] = len(modified)
    report["summary"]["current_added"] = len(added)
    report["latest_patch"] = L2
    report["latest_patch_note"] = ("Hash-bound preservation manifest carried forward by provenance layers (user-authorized "
                                   "2026-10-28); baseline hashes remain unchanged.")
    report["patch_layers"] = [
        {"layer": L1, "source": f"{zip_path.name} sha256 {hashlib.sha256(zip_path.read_bytes()).hexdigest()}", "transitions": l1},
        {"layer": L2, "source": "candidate tree (git archive of the release candidate commit)", "transitions": l2},
    ]
    report["generator"] = "reports/override-evidence/build_v321_preservation_layers.py"
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: v321 manifest carried forward L1={len(l1)} L2={len(l2)} modified={len(modified)} added={len(added)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
