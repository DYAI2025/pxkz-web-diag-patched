#!/usr/bin/env python3
"""Validate legacy v1/v1.1/v1.2 plus default five-class v1.3 batch contracts."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch_contract import (
    V13_CLASSIFICATIONS, classification_counts, classification_names, contract_path, headers, load_contract,
    load_manifest, parse_csv, read_xlsx_sheet, requiredness_counts, sha256_file, specs_by_name,
)

ALIASES = [
    "company_name", "company_website", "prospect_name", "prospect_salutation", "call_compliance_status",
    "call_compliance_note", "lead_source", "consultant_name", "meeting_description", "offer_process",
    "website_analysis_report", "agency_name", "verified_finding",
]
PRODUCTION = [
    "campaign_id", "customer_language", "website_role", "primary_customer_type", "lead_source_current",
    "compliance_status", "do_not_contact", "jurisdiction", "contact_type", "ai_disclosure_required",
    "recording_status", "meeting_offer", "meeting_timezone",
]
EXPECTED_COUNTS = {
    "INTERNAL_RECORD": 48,
    "EL_RUNTIME_REQUIRED": 3,
    "EL_RUNTIME_DEFAULTED": 18,
    "OPTIONAL": 14,
    "PRODUCTION_GATE_ONLY": 13,
}


def fail(m: str) -> int:
    print("FAIL: " + m, file=sys.stderr)
    return 1


def pad(r, w):
    return list(r) + [None] * max(0, w - len(r))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_batch_contract.py <skill-dir>")
    root = Path(argv[1]).resolve()
    manifest = load_manifest(root / "contracts/contract-manifest.json")
    versions = ("v1", "v1.1", "v1.2", "v1.3")
    paths = {v: contract_path(v, root) for v in versions}
    cs = {v: load_contract(p) for v, p in paths.items()}
    ds = {v: sha256_file(p) for v, p in paths.items()}
    hs = {v: headers(c) for v, c in cs.items()}

    if manifest.get("default_contract_selector") != "v1.3" or manifest.get("contract_sha256") != ds["v1.3"]:
        return fail("manifest does not pin default v1.3 digest")
    if [len(hs[v]) for v in versions] != [82, 83, 96, 96]:
        return fail("field count drift")
    if hs["v1.1"][:82] != hs["v1"] or hs["v1.1"][-1] != "customer_email":
        return fail("v1.1 additive boundary drift")
    if hs["v1.2"][:83] != hs["v1.1"] or hs["v1.2"][-13:] != ALIASES:
        return fail("v1.2 provider alias boundary drift")
    if hs["v1.3"] != hs["v1.2"]:
        return fail("v1.3 must preserve exact v1.2 96-column header order")
    if requiredness_counts(cs["v1.2"]) != {"YES": 51, "YES*": 1, "RECOMMENDED": 21, "OPTIONAL": 23}:
        return fail("v1.2 requiredness drift")

    specs13 = specs_by_name(cs["v1.3"])
    seen_classes = {spec.get("classification") for spec in specs13.values()}
    if seen_classes != V13_CLASSIFICATIONS:
        return fail(f"v1.3 classification vocabulary drift: {seen_classes}")
    if classification_counts(cs["v1.3"]) != EXPECTED_COUNTS or cs["v1.3"].get("classification_counts") != EXPECTED_COUNTS:
        return fail("v1.3 classification counts drift")
    if specs13["customer_email"].get("classification") != "OPTIONAL":
        return fail("customer_email must be OPTIONAL in v1.3")
    if specs13["prospect_name"].get("classification") != "EL_RUNTIME_DEFAULTED":
        return fail("prospect_name must be compiler-defaulted rather than source-required")
    if specs13["call_compliance_note"].get("classification") != "EL_RUNTIME_DEFAULTED":
        return fail("call_compliance_note must be compiler-defaulted")
    if classification_names(cs["v1.3"], "PRODUCTION_GATE_ONLY") != PRODUCTION:
        return fail("v1.3 production-gate-only field set drift")

    runtime_union = set(classification_names(cs["v1.3"], "EL_RUNTIME_REQUIRED")) | set(classification_names(cs["v1.3"], "EL_RUNTIME_DEFAULTED"))
    if not set(ALIASES) <= runtime_union:
        return fail("all observed current-agent variables must be runtime required/defaulted in v1.3")
    if set(classification_names(cs["v1.3"], "EL_RUNTIME_REQUIRED")) != {"phone_number", "company_name", "company_website"}:
        return fail("v1.3 EL_RUNTIME_REQUIRED set drift")

    binding = cs["v1.3"].get("provider_binding", {})
    if binding.get("observed_agent_required_dynamic_variables_2026_08_28") != ALIASES:
        return fail("v1.3 observed current-agent binding drift")
    if binding.get("elevenlabs_transport_required") != ["phone_number"]:
        return fail("v1.3 transport binding drift")
    if specs13["call_compliance_status"].get("constraints", {}).get("enum") != ["APPROVED", "BLOCKED", "LEGAL_REVIEW_REQUIRED"]:
        return fail("call compliance enum drift")

    fixtures = manifest.get("golden_fixtures", {})
    h13, rows13, _ = parse_csv(root / fixtures["v1_3_simulation_csv"])
    if h13 != hs["v1.3"] or not rows13:
        return fail("v1.3 simulation fixture drift")
    vals = dict(zip(h13, rows13[0]))
    missing = [x for x in ALIASES if not vals.get(x, "").strip()]
    if missing:
        return fail("v1.3 simulation missing observed agent variables: " + ",".join(missing))

    xlsx = root / fixtures["v1_xlsx_template"]
    batch_rows = read_xlsx_sheet(xlsx, "Batch_Template")
    xh = ["" if v is None else str(v) for v in pad(batch_rows[0], 82)[:82]]
    if xh != hs["v1"]:
        return fail("legacy v1 XLSX header drift")
    excluded = cs["v1.3"].get("excluded_special_override_columns", [])
    if excluded != ["language", "first_message", "system_prompt", "voice_id"] or any(x in hs["v1.3"] for x in excluded):
        return fail("special override exclusion drift")

    print("PASS: batch contracts v1=82 v1.1=83 v1.2=96 v1.3=96 five_class={} sha={}".format(EXPECTED_COUNTS, ds["v1.3"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
