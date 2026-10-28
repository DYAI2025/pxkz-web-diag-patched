"""Frozen legacy oracles: default pipeline output must stay byte-identical.

Hashes were frozen from the pre-patch baseline commit (see the golden file).
A mismatch means the default (no priority context, no VC03 admission) path
changed, which the patch order forbids (INV-02, INV-05, INV-06).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = json.loads((ROOT / "evals/fixtures/golden/legacy-oracles.v1.json").read_text(encoding="utf-8"))
STEPS = (
    ("scored", ".scored.json"), ("plan", ".plan.json"), ("model", ".model.json"),
    ("batch_csv", ".batch.csv"), ("internal", ".internal.json"),
)


def run(*args: str) -> int:
    return subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True).returncode


def build(fixture: str, out: Path) -> dict[str, Path]:
    p = {kind: out / f"{fixture}{suffix}" for kind, suffix in STEPS}
    run("scripts/compute_score.py", f"evals/fixtures/{fixture}.json", str(p["scored"]))
    run("scripts/build_visualization_plan.py", str(p["scored"]), str(p["plan"]))
    run("scripts/build_client_report_model.py", str(p["scored"]), str(p["model"]), "--visual-plan", str(p["plan"]))
    run("scripts/build_elevenlabs_batch_csv.py", str(p["scored"]), str(p["batch_csv"]))
    run("scripts/build_internal_analysis_report.py", str(p["scored"]), str(p["internal"]))
    return p


class LegacyOracleTests(unittest.TestCase):
    def test_default_outputs_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fixture, expected in GOLDEN["cases"].items():
                paths = build(fixture, Path(tmp))
                for kind, _ in STEPS:
                    with self.subTest(fixture=fixture, output=kind):
                        p = paths[kind]
                        actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "FAILS_CLOSED"
                        self.assertEqual(actual, expected[kind])
                if expected["lever_ids"] is not None:
                    model = json.loads(paths["model"].read_text(encoding="utf-8"))
                    self.assertEqual([f["id"] for f in model["findings"]], expected["lever_ids"])


if __name__ == "__main__":
    unittest.main()
