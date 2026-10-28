#!/usr/bin/env python3
"""Record one authorized patch as a new provenance layer in the v3.2.1 preservation manifest.

Baseline hashes never change. Every controlled path whose hash differs from what the manifest
currently records gets a transition row (previous -> current) in a new patch layer named after
the patch; modified/added rows are updated or created with that patch as reason. Deletions are
refused. Re-running for the same patch replaces that patch's layer, so the step is idempotent.

Usage: add_v321_patch_layer.py <skill-dir> <PATCH_ID> <source-note>
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 1
    root, patch, source = Path(argv[1]).resolve(), argv[2], argv[3]
    spec = importlib.util.spec_from_file_location("v321", root / "scripts/validate_strategic_relevance_v321_preservation.py")
    v321 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v321)
    current = v321.controlled(root)

    manifest_path = root / "reports/strategic-relevance-v321-preservation.json"
    report = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = {row["path"]: row["sha256"] for row in report["baseline_files"]}
    modified = {row["path"]: row for row in report["modified_files"]}
    added = {row["path"]: row for row in report["added_files"]}
    # Roll back a previous run of this patch so its layer is recomputed against the prior state.
    for layer in [layer for layer in report["patch_layers"] if layer.get("layer") == patch]:
        for t in layer["transitions"]:
            rel, previous = t["path"], t["previous_sha256"]
            if previous is None:
                added.pop(rel, None)
            elif rel in base and previous == base[rel] and modified.get(rel, {}).get("reason") == patch:
                modified.pop(rel, None)
            elif rel in modified:
                modified[rel]["current_sha256"] = previous
            elif rel in added:
                added[rel]["current_sha256"] = previous
    report["patch_layers"] = [layer for layer in report["patch_layers"] if layer.get("layer") != patch]
    recorded = {**base, **{p: r["current_sha256"] for p, r in {**modified, **added}.items()}}
    deleted = sorted(set(recorded) - set(current))
    if deleted:
        raise SystemExit("FAIL: deletions are not allowed: " + ", ".join(deleted))
    transitions = [
        {"path": rel, "previous_sha256": recorded.get(rel), "current_sha256": sha}
        for rel, sha in sorted(current.items()) if recorded.get(rel) != sha
    ]
    if not transitions:
        print(f"PASS: no changes to record for {patch}")
        return 0
    for t in transitions:
        rel = t["path"]
        if rel in modified:
            modified[rel]["current_sha256"] = t["current_sha256"]
        elif rel in added:
            added[rel]["current_sha256"] = t["current_sha256"]
        elif rel in base:
            modified[rel] = {"path": rel, "baseline_sha256": base[rel], "reason": patch, "current_sha256": t["current_sha256"]}
        else:
            added[rel] = {"path": rel, "reason": patch, "current_sha256": t["current_sha256"]}
    report["modified_files"] = sorted(modified.values(), key=lambda r: r["path"])
    report["added_files"] = sorted(added.values(), key=lambda r: r["path"])
    report["patch_layers"].append({"layer": patch, "source": source, "transitions": transitions})
    report["modified_file_count"] = len(report["modified_files"])
    report["summary"]["current_modified"] = len(report["modified_files"])
    report["summary"]["current_added"] = len(report["added_files"])
    report["latest_patch"] = patch
    report["generator"] = "reports/override-evidence/build_v321_preservation_layers.py + reports/override-evidence/add_v321_patch_layer.py"
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {patch} layer recorded with {len(transitions)} transitions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
