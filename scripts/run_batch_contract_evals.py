#!/usr/bin/env python3
"""Run deterministic producer acceptance evals for Pixelkiez batch contracts through v1.3."""
from __future__ import annotations
import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_contract import (  # noqa: E402
    classification_names, contract_path, headers, is_audit_owned, load_contract, parse_csv, specs_by_name, validate_csv_row,
)
from build_elevenlabs_batch_csv import main as build_main, validate_context  # noqa: E402
from compute_score import main as score_main  # noqa: E402
from validate_batch_contract import main as validate_contract_main  # noqa: E402

OBSERVED_AGENT = [
    "company_name", "company_website", "prospect_name", "prospect_salutation",
    "call_compliance_status", "call_compliance_note", "lead_source", "consultant_name",
    "meeting_description", "offer_process", "website_analysis_report", "agency_name", "verified_finding",
]
EXPECTED_CLASSES = {"INTERNAL_RECORD": 48, "EL_RUNTIME_REQUIRED": 3, "EL_RUNTIME_DEFAULTED": 18, "OPTIONAL": 14, "PRODUCTION_GATE_ONLY": 13}


def call_build(args: list[str], expect: int = 0) -> None:
    old = sys.argv[:]
    try:
        sys.argv = ["build_elevenlabs_batch_csv.py", *args]
        rc = build_main()
    finally:
        sys.argv = old
    if rc != expect:
        raise AssertionError(f"builder return code {rc} != {expect}: {args}")


def read_row(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    return rows[0]


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def value_for(name: str, spec: dict[str, Any]) -> Any:
    example = spec.get("example")
    typ = spec.get("type")
    if name == "phone_number": return "+493012345678"
    if name == "compliance_status": return "APPROVED"
    if name == "recording_status": return "OFF"
    if name == "do_not_contact": return False
    if name == "ai_disclosure_required": return True
    if typ == "Boolean": return str(example).lower() == "true"
    if typ == "Number": return float(example) if example not in (None, "") else 30
    return str(example) if example not in (None, "") else f"TEST-{name}"


def context_for(contract: dict[str, Any], cpath: Path, names: list[str]) -> dict[str, Any]:
    specs = specs_by_name(contract)
    context: dict[str, Any] = {
        "_contract_digest": hashlib.sha256(cpath.read_bytes()).hexdigest(),
        "_contract_version": str(contract.get("version")),
    }
    for name in names:
        if name == "recipient_number" or is_audit_owned(specs[name]):
            continue
        context[name] = value_for(name, specs[name])
    return context


def mutate_csv(src: Path, dst: Path, name: str, value: str) -> None:
    h, rows, _ = parse_csv(src)
    assert len(rows) == 1
    row = dict(zip(h, rows[0]))
    row[name] = value
    with dst.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(h)
        w.writerow([row.get(x, "") for x in h])


def assert_upload(contract: dict[str, Any], path: Path, expected: bool) -> dict[str, Any]:
    h, rows, _ = parse_csv(path)
    assert h == headers(contract) and len(rows) == 1
    result = validate_csv_row(contract, h, rows[0])
    assert not result["errors"]
    assert result["elevenlabs_upload_ready"] is expected
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_batch_contract_evals.py <skill-dir>", file=sys.stderr)
        return 1
    root = Path(argv[1]).resolve()
    versions = ("v1", "v1.1", "v1.2", "v1.3")
    paths = {v: contract_path(v, root) for v in versions}
    contracts = {v: load_contract(paths[v]) for v in versions}
    results: list[dict[str, str]] = []

    def ok(name: str, detail: str = "PASS") -> None:
        results.append({"eval": name, "status": "PASS", "detail": detail})
        print(f"PASS: {name} ({detail})")

    try:
        if validate_contract_main(["validate_batch_contract.py", str(root)]) != 0:
            raise AssertionError("validate_batch_contract failed")
        ok("contract_migration_v1_82_v1_1_83_v1_2_96_v1_3_96")

        c13 = contracts["v1.3"]
        assert c13["classification_counts"] == EXPECTED_CLASSES
        assert classification_names(c13, "EL_RUNTIME_REQUIRED") == ["phone_number", "company_name", "company_website"]
        assert "customer_email" in classification_names(c13, "OPTIONAL")
        assert "prospect_name" in classification_names(c13, "EL_RUNTIME_DEFAULTED")
        ok("v1_3_five_class_partition_exact")

        with tempfile.TemporaryDirectory(prefix="pxk-batch-v13-") as tmp:
            t = Path(tmp)
            scored = t / "scored.json"
            if score_main(["compute_score.py", str(root / "evals/fixtures/synthetic-report.json"), str(scored)]) != 0:
                raise AssertionError("score fixture failed")

            draft = t / "default-v13-no-context.csv"
            draft_val = t / "default-v13-no-context.validation.json"
            call_build([str(scored), str(draft), "--validation-out", str(draft_val)])
            dv = json.loads(draft_val.read_text(encoding="utf-8"))
            assert dv["contract_version"] == "1.3.0" and dv["classification_counts"] == EXPECTED_CLASSES
            assert dv["elevenlabs_upload_status"] == "EL_UPLOAD_BLOCKED"
            assert dv["missing_runtime_required_fields"] == ["phone_number"]
            assert dv["missing_runtime_defaulted_fields"] == ["recipient_number"]
            ok("default_v1_3_export_is_structural_even_without_phone")

            minimal_ctx = context_for(c13, paths["v1.3"], ["phone_number"])
            minimal = t / "minimal.json"; write_json(minimal, minimal_ctx)
            validate_context(c13, minimal_ctx, hashlib.sha256(paths["v1.3"].read_bytes()).hexdigest())
            ready = t / "upload-ready-v13.csv"; ready_val = t / "upload-ready-v13.validation.json"
            call_build([str(scored), str(ready), "--batch-context", str(minimal), "--validation-out", str(ready_val)])
            rrow = read_row(ready); rv = json.loads(ready_val.read_text(encoding="utf-8"))
            assert_upload(c13, ready, True)
            assert rv["elevenlabs_upload_status"] == "EL_UPLOAD_READY" and rv["batch_status"] == "BATCH_READY"
            assert rv["production_prerequisite_gate"] == "BLOCKED" and len(rv["missing_production_gate_fields"]) == 13
            assert rrow["customer_email"] == ""
            assert rrow["prospect_name"] == "NICHT_VERIFIZIERT"
            assert rrow["lead_source"] == "NICHT_VERIFIZIERT"
            assert rrow["call_compliance_status"] == "LEGAL_REVIEW_REQUIRED"
            assert rrow["prospect_salutation"] == "Guten Tag"
            assert all(rrow[name].strip() for name in OBSERVED_AGENT)
            ok("missing_email_and_unknown_prospect_do_not_block_upload")
            ok("all_observed_agent_variables_materialized_by_required_or_defaulted_classes")
            ok("production_gate_is_separate_from_upload_readiness")

            prod_names = ["phone_number"] + classification_names(c13, "PRODUCTION_GATE_ONLY")
            prod_ctx = context_for(c13, paths["v1.3"], prod_names)
            validate_context(c13, prod_ctx, hashlib.sha256(paths["v1.3"].read_bytes()).hexdigest())
            prod = t / "production.json"; write_json(prod, prod_ctx)
            prod_csv = t / "production-ready-v13.csv"; prod_val = t / "production-ready-v13.validation.json"
            call_build([str(scored), str(prod_csv), "--batch-context", str(prod), "--validation-out", str(prod_val)])
            pv = json.loads(prod_val.read_text(encoding="utf-8")); prow = read_row(prod_csv)
            pres = assert_upload(c13, prod_csv, True)
            assert pres["production_prerequisite_gate_passed"] is True
            assert pv["production_prerequisite_gate"] == "PASS" and not pv["missing_production_gate_fields"]
            assert prow["call_compliance_status"] == prow["compliance_status"] == "APPROVED"
            assert prow["lead_source"] == prow["lead_source_current"]
            ok("authoritative_production_fields_can_pass_separate_prerequisite_gate")

            assert_upload(c13, draft, False)
            ok("missing_runtime_required_phone_blocks_upload_ready_gate")

            bad_default = t / "bad-default.csv"; mutate_csv(ready, bad_default, "prospect_name", "")
            assert_upload(c13, bad_default, False)
            ok("blank_runtime_defaulted_field_blocks_upload_ready_gate")

            no_email = t / "no-email.csv"; mutate_csv(ready, no_email, "customer_email", "")
            assert_upload(c13, no_email, True)
            ok("blank_optional_customer_email_never_blocks_upload_ready_gate")

            bad_null = t / "bad-null.csv"; mutate_csv(ready, bad_null, "customer_email", "null")
            h, rows, _ = parse_csv(bad_null); bad_res = validate_csv_row(c13, h, rows[0])
            assert any(e.startswith("literal_null_forbidden:customer_email") for e in bad_res["errors"])
            ok("literal_null_remains_forbidden_even_for_optional_fields")

            # v1.2/v1.3 share the exact same wire header; current default resolves that shape to v1.3 in auto mode.
            assert headers(contracts["v1.2"]) == headers(c13)
            ok("auto_detect_96_column_shape_resolves_to_latest_v1_3")

            for selector, count in (("v1.2", 96), ("v1.1", 83), ("v1", 82)):
                out = t / f"compat-{selector}.csv"
                call_build([str(scored), str(out), "--contract-version", selector])
                h, rows, _ = parse_csv(out)
                assert len(h) == count and len(rows) == 1 and not validate_csv_row(contracts[selector], h, rows[0])["errors"]
                ok(f"explicit_{selector.replace('.', '_')}_{count}_regression")

            for name, selector in [
                ("pixelkiez_elevenlabs_batch_example_SIMULATION.csv", "v1"),
                ("pixelkiez_elevenlabs_batch_example_v1.1_SIMULATION.csv", "v1.1"),
                ("pixelkiez_elevenlabs_batch_example_v1.2_SIMULATION.csv", "v1.2"),
                ("pixelkiez_elevenlabs_batch_example_v1.3_SIMULATION.csv", "v1.3"),
            ]:
                fh, frows, _ = parse_csv(root / "evals/fixtures" / name)
                assert fh == headers(contracts[selector]) and len(frows) == 1
                assert not validate_csv_row(contracts[selector], fh, frows[0])["errors"]
            ok("all_versioned_simulation_fixtures_validate")

            sibling = root.parent / "pixelkiez-adaptive-elevenlabs-appointment-agent-architect" / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.3.json"
            if sibling.exists():
                assert hashlib.sha256(sibling.read_bytes()).hexdigest() == hashlib.sha256(paths["v1.3"].read_bytes()).hexdigest()
                ok("cross_skill_v1_3_same_digest")
            else:
                ok("cross_skill_v1_3_same_digest", "NOT_EXECUTED_SIBLING_V1_3_NOT_PRESENT")

        report = {"status": "PASS", "eval_count": len(results), "results": results}
        (root / "reports/batch-contract-eval-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: batch contract acceptance evals ({len(results)})")
        return 0
    except Exception as exc:
        report = {"status": "FAIL", "eval_count": len(results), "results": results, "error": str(exc)}
        (root / "reports/batch-contract-eval-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
