#!/usr/bin/env python3
"""Run deterministic truth-discipline regression tests for audit-to-voice evidence projection."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_policy import derive_voice_evidence_class  # noqa: E402


def assert_eq(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_truth_discipline_evals.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    try:
        base = json.loads((root / "evals/fixtures/synthetic-report.json").read_text(encoding="utf-8"))
        findings = {f["id"]: f for f in base["findings"]}
        metrics = {m["id"]: m for m in base["metrics"]}

        assert_eq(derive_voice_evidence_class(base, findings["F-003"]), "VERIFIED_FACT", "observed direct evidence")
        assert_eq(derive_voice_evidence_class(base, findings["F-002"]), "VERIFIED_FACT", "measured/observed direct evidence")

        inferred = json.loads((root / "evals/fixtures/truth-discipline-inferred-risk.json").read_text(encoding="utf-8"))
        inf_f = next(f for f in inferred["findings"] if f["id"] == "F-001")
        assert_eq(derive_voice_evidence_class(inferred, inf_f), "HYPOTHESIS", "inferred_risk")

        unknown = deepcopy(base)
        uf = next(f for f in unknown["findings"] if f["id"] == "F-003")
        um = next(m for m in unknown["metrics"] if m["id"] == uf["metric_refs"][0])
        um["measurement_class"] = "not_assessed"
        um["evidence_grade"] = "E8"
        um["score"] = None
        assert_eq(derive_voice_evidence_class(unknown, uf), "UNKNOWN", "not_assessed")

        unresolved = deepcopy(base)
        rf = next(f for f in unresolved["findings"] if f["id"] == "F-003")
        rf["metric_refs"] = ["DOES-NOT-EXIST"]
        try:
            derive_voice_evidence_class(unresolved, rf)
        except ValueError:
            pass
        else:
            raise AssertionError("unresolved metric_refs did not fail closed")

        overclaim = deepcopy(inferred)
        of = next(f for f in overclaim["findings"] if f["id"] == "F-001")
        of["voice_hook"] = {"evidence_class": "VERIFIED_FACT"}
        try:
            derive_voice_evidence_class(overclaim, of)
        except ValueError:
            pass
        else:
            raise AssertionError("declared VERIFIED_FACT upgraded inferred_risk")

        weaker = deepcopy(base)
        wf = next(f for f in weaker["findings"] if f["id"] == "F-003")
        wf["voice_hook"] = {"evidence_class": "HYPOTHESIS"}
        assert_eq(derive_voice_evidence_class(weaker, wf), "HYPOTHESIS", "explicit conservative downgrade")

        with tempfile.TemporaryDirectory(prefix="pxk-truth-") as tmp:
            t = Path(tmp)
            scored = t / "truth-scored.json"
            subprocess.run([sys.executable, str(root / "scripts/compute_score.py"), str(root / "evals/fixtures/truth-discipline-inferred-risk.json"), str(scored)], check=True, capture_output=True, text=True)
            csv_path = t / "truth.csv"
            subprocess.run([sys.executable, str(root / "scripts/build_elevenlabs_batch_csv.py"), str(scored), str(csv_path)], check=True, capture_output=True, text=True)
            packet = t / "packet.json"
            subprocess.run([sys.executable, str(root / "scripts/build_website_audit_packet.py"), str(scored), str(packet)], check=True, capture_output=True, text=True)
            row = next(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline="")))
            pkt = json.loads(packet.read_text(encoding="utf-8"))
            csv_hook = next((row[f"audit_hook_{i}_evidence_class"] for i in (1, 2, 3) if row.get(f"audit_hook_{i}_id") == "F-001"), "")
            packet_hook = next((h["evidence_class"] for h in pkt.get("conversation_hooks", []) if h.get("finding_id") == "F-001"), "")
            assert_eq(csv_hook, "HYPOTHESIS", "CSV truth projection")
            assert_eq(packet_hook, "HYPOTHESIS", "packet truth projection")
            if "Modellbasierte Ableitung" in row.get("verified_finding", ""):
                raise AssertionError("inferred finding leaked into verified_finding")

        print("PASS: truth-discipline evals (8 cases)")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
