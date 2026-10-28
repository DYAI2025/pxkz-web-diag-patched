#!/usr/bin/env python3
"""Executable customer-priority integration and immutable-score regression fixtures."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
FIX = ROOT / "evals" / "fixtures"


def run(cmd: list[str], expected_rc: int = 0) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if (result.returncode == 0) != (expected_rc == 0):
        raise RuntimeError(f"cmd rc={result.returncode} expected={expected_rc}\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def main() -> int:
    fixture = FIX / "synthetic-report.json"
    tie_fixture = FIX / "branch-priority-tie-report.SYNTHETIC.json"
    context = FIX / "branch-priority-context.SYNTHETIC.json"
    catalog = FIX / "branch-priority-catalog.SYNTHETIC.json"
    digest = hashlib.sha256(catalog.read_bytes()).hexdigest()
    protected = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("assets/measurement-registry.json", "scripts/compute_score.py")
    }
    with tempfile.TemporaryDirectory(prefix="pxk-priority-eval-") as temp:
        t = Path(temp)
        legacy, ranked, decision = (t / "legacy.json", t / "ranked.json", t / "decision.json")
        cmd = [PY, str(ROOT / "scripts/build_client_report_model.py"), str(fixture)]
        tie_cmd = [PY, str(ROOT / "scripts/build_client_report_model.py"), str(tie_fixture)]
        run(cmd + [str(legacy)])
        base = tie_cmd + [str(ranked), "--priority-context", str(context), "--priority-catalog", str(catalog)]
        run(base, expected_rc=1)  # no digest may not trust external catalog
        run(base + ["--priority-catalog-sha256", "0" * 64], expected_rc=1)
        # Synthetic profiles are test data: honored only with the explicit test flag and only for genuine ties.
        run(base + ["--priority-catalog-sha256", digest, "--priority-allow-synthetic", "--priority-decision-out", str(decision)])
        old = json.loads(legacy.read_text())
        new = json.loads(ranked.read_text())
        d = json.loads(decision.read_text())
        old_ids = [row["id"] for row in old["findings"]]
        new_ids = [row["id"] for row in new["findings"]]
        if old_ids != ["F-001", "F-003", "F-004", "F-002"]:
            raise RuntimeError(f"unexpected synthetic baseline: {old_ids}")
        if new_ids != ["F-001", "F-003", "F-004", "F-005"]:
            raise RuntimeError(f"industry priority not honored or severity broken: {new_ids}")
        if old["cover"] != new["cover"]:
            raise RuntimeError("score or cover mutated")
        if d["profile_id"] != "SYNTHETIC_SAMPLE_01" or d["score_changed"] is not False:
            raise RuntimeError("priority provenance invalid")
        if d["legacy_selected_ids"] != old_ids or not d["deviations"] or any(
            x["reason"] != "APPROVED_PROFILE_GENUINE_TIE_ORDER" or x["profile_id"] != "SYNTHETIC_SAMPLE_01" for x in d["deviations"]
        ):
            raise RuntimeError("deviation from legacy selection lacks machine-readable reason/profile reference")
        non_tie = cmd + [str(t / "non-tie.json"), "--priority-context", str(context), "--priority-catalog", str(catalog),
                         "--priority-catalog-sha256", digest, "--priority-allow-synthetic"]
        run(non_tie)
        if [x["id"] for x in json.loads((t / "non-tie.json").read_text())["findings"]] != old_ids:
            raise RuntimeError("profile reordered findings that are not a genuine severity/confidence tie")
        no_flag = tie_cmd + [str(t / "no-flag.json"), "--priority-context", str(context), "--priority-catalog", str(catalog),
                             "--priority-catalog-sha256", digest]
        run(no_flag)
        if [x["id"] for x in json.loads((t / "no-flag.json").read_text())["findings"]] != old_ids:
            raise RuntimeError("synthetic test profile changed selection outside test mode")
        if "SYNTHETIC_SAMPLE_01" in json.dumps(new):
            raise RuntimeError("internal sector profile leaked into customer projection")
        no_profile = cmd + [str(t / "no-profile.json"), "--priority-context", str(context)]
        run(no_profile)
        no = json.loads((t / "no-profile.json").read_text())
        if [x["id"] for x in no["findings"]] != old_ids:
            raise RuntimeError("missing approved profile must leave default selection unchanged")
        for name, prior_hash in protected.items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != prior_hash:
                raise RuntimeError("protected score core changed during customer selection")
    print("PASS: contextual customer selection, genuine-tie-only profile order, synthetic test-mode gate, SHA-pinned catalog, fallback, score neutrality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
