#!/usr/bin/env python3
"""Validate the Active Core Migration 48/48 contract-path evidence and protected invariants."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


# Approved, hash-chained changes to protected files. Reasons and the paths they may touch are fixed here, so the
# change report cannot widen them; every row must start from the current effective digest of its path.
PROTECTED_CHANGE_REPORT = "reports/active-measurement-protected-changes.json"
ALLOWED_PROTECTED_CHANGES = {
    "IMPRESSUM_CUSTOMER_RISK_SCHEMA": {"schemas/diagnosis-report.schema.json"},
    "VIBECHECK03_DIAGNOSTICS_SCHEMA": {"schemas/diagnosis-report.schema.json"},
}
SHA_RX = re.compile(r"^[0-9a-f]{64}$")


def apply_protected_changes(protected: dict[str, str], report: dict | None) -> dict[str, str]:
    effective = dict(protected)
    if report is None:
        return effective
    if report.get("status") != "PASS":
        raise ValueError("protected change report status is not PASS")
    for row in report.get("changes") or []:
        rel, reason = row.get("path"), row.get("reason")
        if rel not in effective:
            raise ValueError(f"protected change for path that is not protected: {rel}")
        if rel not in ALLOWED_PROTECTED_CHANGES.get(reason, set()):
            raise ValueError(f"protected change reason not allowed for {rel}: {reason}")
        prev, cur = row.get("previous_sha256"), row.get("current_sha256")
        if not (isinstance(prev, str) and SHA_RX.match(prev) and isinstance(cur, str) and SHA_RX.match(cur)):
            raise ValueError(f"protected change for {rel} needs previous/current sha256")
        if prev != effective[rel]:
            raise ValueError(f"protected change chain broken for {rel}: {prev} != {effective[rel]}")
        effective[rel] = cur
    return effective


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_full_48_active.py <skill-dir>")
    root = Path(argv[1]).resolve()
    try:
        baseline = load(root / "reports/active-measurement-protected-baseline.json")
        matrix = load(root / "reports/48-metric-execution-matrix.json")
        active = load(root / "reports/core-active-eval-results.json")
        mutations = load(root / "reports/core-active-mutation-test-report.json")
        score = load(root / "reports/score-reconciliation-report.json")
        analysis = load(root / "reports/analysis-report-reconciliation.json")
        determinism = load(root / "reports/core-active-determinism-report.json")
    except Exception as exc:
        return fail(f"active migration report load failed: {exc}")

    errors: list[str] = []
    try:
        current_digest = subprocess.check_output([sys.executable, str(root / "scripts/pipeline_ledger.py"), "digest", str(root)], text=True).strip()
    except Exception as exc:
        return fail(f"artifact digest unavailable: {exc}")
    for label, report in (("active", active), ("mutations", mutations), ("score", score), ("analysis", analysis), ("determinism", determinism)):
        if report.get("artifact_digest") != current_digest:
            errors.append(f"{label} proof artifact digest stale: {report.get('artifact_digest')} != {current_digest}")
    if matrix.get("total_metrics") != 48 or len(matrix.get("metrics", [])) != 48:
        errors.append("execution matrix must contain exactly 48 rows")
    mids = [x.get("metric_id") for x in matrix.get("metrics", [])]
    if len(set(mids)) != 48:
        errors.append("execution matrix metric IDs must be unique")
    if active.get("status") != "PASS" or active.get("suite") != "FULL_48_ACTIVE":
        errors.append("FULL_48_ACTIVE eval status must be PASS")
    for key in ("total_registry_metrics", "execution_ready", "evidence_ready", "score_admitted", "report_reconciled"):
        if active.get(key) != 48:
            errors.append(f"active eval {key} must equal 48")
    if active.get("required_check_count", 0) < 22:
        errors.append("mandatory FULL_48_ACTIVE check inventory incomplete")
    if active.get("mutation_count", 0) < 15 or mutations.get("status") != "PASS" or mutations.get("detected") != active.get("mutation_count"):
        errors.append("mutation evidence incomplete")
    if score.get("status") != "PASS" or score.get("registry_weights_unchanged") is not True or score.get("compute_score_changed") is not False:
        errors.append("score integrity report failed")
    if score.get("fixture_only") is not True:
        errors.append("golden score proof must remain explicitly fixture-only")
    if analysis.get("status") != "PASS" or analysis.get("metric_count") != 48:
        errors.append("analysis report reconciliation failed")
    if analysis.get("weighted_contributions") != "RECONCILED" or analysis.get("category_results") != "RECONCILED" or analysis.get("overall_result") != "RECONCILED":
        errors.append("weighted analysis reconciliation incomplete")
    if determinism.get("status") != "PASS" or determinism.get("semantic_digest") != determinism.get("shuffled_semantic_digest"):
        errors.append("semantic determinism failed")
    if determinism.get("scored_report_sha256") != determinism.get("shuffled_scored_report_sha256"):
        errors.append("scored report determinism failed")
    if determinism.get("timestamps_excluded_from_semantic_digest") is not True:
        errors.append("timestamp digest policy not proven")

    try:
        changes_path = root / PROTECTED_CHANGE_REPORT
        protected = apply_protected_changes(baseline.get("protected_files", {}), load(changes_path) if changes_path.is_file() else None)
    except Exception as exc:
        return fail(f"protected change report invalid: {exc}")
    for rel, expected in protected.items():
        path = root / rel
        if not path.exists():
            errors.append(f"protected file missing: {rel}")
            continue
        actual = sha(path)
        if actual != expected:
            errors.append(f"protected file changed: {rel} {actual} != {expected}")

    binding_validator = root / "scripts/validate_core_evidence_bindings.py"
    if binding_validator.exists():
        p = subprocess.run([sys.executable, str(binding_validator), str(root)], text=True, capture_output=True)
        if p.returncode != 0:
            errors.append("binding validator failed: " + (p.stderr or p.stdout).strip())
    else:
        errors.append("binding validator missing")

    if errors:
        return fail("; ".join(errors))
    print("PASS: FULL_48_ACTIVE contract path metrics=48 protected_core=unchanged fixture_only=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
