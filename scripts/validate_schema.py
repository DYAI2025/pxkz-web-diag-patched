#!/usr/bin/env python3
"""Validate schemas, measurement registry and runtime capability registry integrity."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EVIDENCE_GRADES = {f"E{i}" for i in range(1, 9)}
REQUIRED_METRIC_FIELDS = {
    "id", "category", "label_de", "weight", "minimum_public", "score_mode",
    "max_evidence_grade", "capability_id", "test_method", "control_basis", "limitation"
}


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_schema.py <skill-dir>")
    root = Path(argv[1]).resolve()
    try:
        diagnosis = json.loads((root / "schemas/diagnosis-report.schema.json").read_text(encoding="utf-8"))
        client = json.loads((root / "schemas/client-report.schema.json").read_text(encoding="utf-8"))
        batch_context = json.loads((root / "schemas/batch-context.schema.json").read_text(encoding="utf-8"))
        batch_row = json.loads((root / "schemas/batch-row.schema.json").read_text(encoding="utf-8"))
        contract_manifest = json.loads((root / "contracts/contract-manifest.json").read_text(encoding="utf-8"))
        registry = json.loads((root / "assets/measurement-registry.json").read_text(encoding="utf-8"))
        capabilities = json.loads((root / "assets/capability-registry.json").read_text(encoding="utf-8"))
        template = json.loads((root / "templates/client-report-template.json").read_text(encoding="utf-8"))
        analysis_schema = json.loads((root / "schemas/analysis-report.schema.json").read_text(encoding="utf-8"))
        visual_plan_schema = json.loads((root / "schemas/visualization-plan.schema.json").read_text(encoding="utf-8"))
        visual_receipt_schema = json.loads((root / "schemas/visual-render-receipt.schema.json").read_text(encoding="utf-8"))
        visual_catalog = json.loads((root / "templates/visualization-catalog.v2.json").read_text(encoding="utf-8"))
        core_binding_schema = json.loads((root / "schemas/core-evidence-binding.schema.json").read_text(encoding="utf-8"))
        core_execution_schema = json.loads((root / "schemas/core-execution-bundle.schema.json").read_text(encoding="utf-8"))
        core_admission_schema = json.loads((root / "schemas/core-score-admission-report.schema.json").read_text(encoding="utf-8"))
        core_bindings = json.loads((root / "assets/core-evidence-bindings.active.v1.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(str(exc))

    for label, schema in (
        ("core evidence binding", core_binding_schema),
        ("core execution bundle", core_execution_schema),
        ("core score admission", core_admission_schema),
    ):
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            return fail(f"{label} schema must use JSON Schema Draft 2020-12")
        if not str(schema.get("$id", "")).startswith("https://pixelkiez.local/schemas/"):
            return fail(f"{label} schema must have a stable Pixelkiez $id")
    if core_bindings.get("contract_version") != "1.0.0" or core_bindings.get("activation_mode") != "ACTIVE_CORE_ADMISSION":
        return fail("active core binding contract version/mode drift")
    if core_bindings.get("measurement_registry_version") != registry.get("registry_version"):
        return fail("active core binding registry version mismatch")
    if len(core_bindings.get("metrics", [])) != 48 or len({x.get("metric_id") for x in core_bindings.get("metrics", [])}) != 48:
        return fail("active core binding must contain exactly 48 unique metric rows")

    required = {"meta", "coverage", "metrics", "score_summary", "executive_summary", "findings", "visualizations", "roadmap", "sources", "limitations", "missing", "source_needed"}
    if diagnosis.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        return fail("diagnosis schema must use JSON Schema Draft 2020-12")
    if diagnosis.get("type") != "object" or diagnosis.get("additionalProperties") is not False:
        return fail("diagnosis schema root must be a closed object")
    if not required <= set(diagnosis.get("required", [])):
        return fail("diagnosis schema required sections incomplete")
    score_req = set(diagnosis.get("properties", {}).get("score_summary", {}).get("required", []))
    if not {"policy_version", "registry_version", "coverage_percent", "confidence"} <= score_req:
        return fail("score summary must be versioned and coverage-aware")
    if client.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        return fail("client schema must use JSON Schema Draft 2020-12")
    digest = contract_manifest.get("contract_sha256")
    legacy = contract_manifest.get("legacy_v1", {})
    if contract_manifest.get("field_count") != 96 or contract_manifest.get("contract_version") != "1.3.0" or not isinstance(digest, str) or len(digest) != 64:
        return fail("default batch contract manifest must identify v1.3 with 96 fields and a digest")
    expected_classes = {"INTERNAL_RECORD": 48, "EL_RUNTIME_REQUIRED": 3, "EL_RUNTIME_DEFAULTED": 18, "OPTIONAL": 14, "PRODUCTION_GATE_ONLY": 13}
    if contract_manifest.get("classification_model") != "v1.3-five-class-readiness" or contract_manifest.get("classification_counts") != expected_classes:
        return fail("default batch contract manifest must pin the v1.3 five-class readiness model")
    if legacy.get("field_count") != 82 or not isinstance(legacy.get("sha256"), str) or len(legacy.get("sha256", "")) != 64:
        return fail("legacy v1 batch contract manifest binding invalid")
    for label, schema in (("batch context", batch_context), ("batch row", batch_row)):
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            return fail(f"{label} schema must use JSON Schema Draft 2020-12")
        if schema.get("x-generated-from-contract-sha256") != digest:
            return fail(f"{label} schema is not pinned to the shared contract digest")
    if len(batch_row.get("properties", {})) != 96 or set(batch_row.get("required", [])) != set(batch_row.get("properties", {})):
        return fail("default batch row schema must contain and require exactly 96 v1.3 contract columns")
    if "customer_email" not in batch_row.get("properties", {}) or "verified_finding" not in batch_row.get("properties", {}):
        return fail("v1.3 batch row schema must include customer_email and runtime binding aliases")
    try:
        legacy_context = json.loads((root / "schemas/batch-context.v1.schema.json").read_text(encoding="utf-8"))
        legacy_row = json.loads((root / "schemas/batch-row.v1.schema.json").read_text(encoding="utf-8"))
        v11_context = json.loads((root / "schemas/batch-context.v1.1.schema.json").read_text(encoding="utf-8"))
        v11_row = json.loads((root / "schemas/batch-row.v1.1.schema.json").read_text(encoding="utf-8"))
        v12_context = json.loads((root / "schemas/batch-context.v1.2.schema.json").read_text(encoding="utf-8"))
        v12_row = json.loads((root / "schemas/batch-row.v1.2.schema.json").read_text(encoding="utf-8"))
        v13_context = json.loads((root / "schemas/batch-context.v1.3.schema.json").read_text(encoding="utf-8"))
        v13_row = json.loads((root / "schemas/batch-row.v1.3.schema.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"versioned batch schemas invalid: {exc}")
    if len(legacy_row.get("properties", {})) != 82 or "customer_email" in legacy_row.get("properties", {}):
        return fail("legacy v1 row schema must remain exactly 82 fields without customer_email")
    if len(v11_row.get("properties", {})) != 83 or "customer_email" not in v11_row.get("properties", {}):
        return fail("v1.1 row schema must contain 83 fields including customer_email")
    if legacy_context.get("x-generated-from-contract-sha256") != legacy.get("sha256"):
        return fail("legacy v1 context schema digest mismatch")
    if len(v12_row.get("properties", {})) != 96 or any(n not in v12_row.get("properties", {}) for n in ['company_name', 'company_website', 'prospect_name', 'prospect_salutation', 'call_compliance_status', 'call_compliance_note', 'lead_source', 'consultant_name', 'meeting_description', 'offer_process', 'website_analysis_report', 'agency_name', 'verified_finding']):
        return fail("v1.2 row schema must contain 96 fields and all provider aliases")
    previous = contract_manifest.get("previous_v1_1", {})
    if v11_context.get("x-generated-from-contract-sha256") != previous.get("sha256"):
        return fail("v1.1 context schema digest mismatch")
    previous12 = contract_manifest.get("previous_v1_2", {})
    if v12_context.get("x-generated-from-contract-sha256") != previous12.get("sha256"):
        return fail("v1.2 context schema digest mismatch")
    if v13_context.get("x-generated-from-contract-sha256") != digest:
        return fail("v1.3 context schema digest mismatch")
    if len(v13_row.get("properties", {})) != 96 or v13_row.get("x-readiness-model") != "v1.3-five-class-readiness" or v13_row.get("x-classification-counts") != expected_classes:
        return fail("v1.3 row schema must expose all 96 fields plus five-class readiness metadata")
    if v13_row.get("properties", {}).get("customer_email", {}).get("x-v1.3-classification") != "OPTIONAL":
        return fail("v1.3 row schema must classify customer_email as OPTIONAL")
    if v13_row.get("properties", {}).get("prospect_name", {}).get("x-v1.3-classification") != "EL_RUNTIME_DEFAULTED":
        return fail("v1.3 row schema must classify prospect_name as EL_RUNTIME_DEFAULTED")
    if any(name in batch_row.get("properties", {}) for name in ("language", "first_message", "system_prompt", "voice_id")):
        return fail("special ElevenLabs overrides leaked into standard batch row schema")
    diagnosis_props = diagnosis.get("properties", {})
    meta_props = diagnosis_props.get("meta", {}).get("properties", {})
    if "website_language" not in meta_props or "audit_id" not in meta_props:
        return fail("diagnosis meta lacks optional audit_id/website_language batch inputs")
    if "public_business" not in diagnosis_props or "voice_hook" not in diagnosis.get("$defs", {}).get("finding", {}).get("properties", {}):
        return fail("diagnosis schema lacks optional public_business/voice_hook batch mapping inputs")
    if template.get("template_version") != client.get("properties", {}).get("template_version", {}).get("const"):
        return fail("client template version and client schema version differ")
    expected_flow = ["cover", "executive", "visualizations", "findings", "roadmap", "closing"]
    if [x.get("id") for x in template.get("page_flow", [])] != expected_flow:
        return fail("client template page flow must match the chart-led 12-page architecture")
    if template.get("output") != "pdf" or "PowerPoint generation" not in template.get("prohibited", []):
        return fail("client template must be PDF-only")
    page_budget = template.get("customer_page_budget", {})
    if page_budget.get("hard_max") != 12:
        return fail("customer PDF hard page limit must be 12")
    visual_gate = template.get("visual_story_gate", {})
    if visual_gate.get("completed_customer_pdf_min_real_charts") != 4 or visual_gate.get("completed_customer_pdf_max_real_charts") != 7:
        return fail("visual story gate must require four to seven approved customer visuals")
    if visual_gate.get("approved_template_catalog") != "templates/visualization-catalog.v2.json":
        return fail("visual story gate must bind the v2 visualization catalog")
    if visual_gate.get("no_chartless_customer_pdf") is not True or visual_gate.get("no_benchmark_without_context") is not True:
        return fail("visual story gate must prohibit chartless PDFs and unsourced benchmarks")
    arch = template.get("visual_architecture", {})
    expected_arch = {
        "version": "1.0",
        "primary_spec_grammar": "VEGA_LITE",
        "primary_document_renderer": "WEASYPRINT",
        "deterministic_no_runtime_fallback": "PIXELKIEZ_SVG_FALLBACK",
        "min_generated_visuals": 4,
        "max_embedded_visuals": 7,
    }
    for key, value in expected_arch.items():
        if arch.get(key) != value:
            return fail(f"visual architecture drift: {key}")
    if arch.get("legacy_reportlab_customer_default") is not False or arch.get("render_receipt_required") is not True:
        return fail("WeasyPrint/receipt must be the customer default")
    semantic_gate = template.get("semantic_story_gate", {})
    if semantic_gate.get("policy_version") != "1.0" or semantic_gate.get("final_semantic_qa_required") is not True:
        return fail("semantic story policy/gate missing")
    if semantic_gate.get("presentation_modes") != ["NUMBER_FIRST", "EVIDENCE_VISUAL", "SHORT_TEXT"]:
        return fail("semantic presentation modes drift")
    internal = template.get("internal_analysis_report", {})
    if internal.get("json") != "analysis_report.json" or internal.get("markdown") != "analysis_report.md" or internal.get("every_canonical_metric_exactly_once") is not True:
        return fail("mandatory internal JSON/Markdown analysis contract missing")
    brand_gate = template.get("brand_rendering_gate", {})
    if brand_gate.get("body_min_pt") != 12 or brand_gate.get("chart_label_min_pt") != 10 or brand_gate.get("serif_fonts") != "prohibited":
        return fail("brand rendering typography gate drift")
    for label, schema in (("analysis report", analysis_schema), ("visualization plan", visual_plan_schema), ("visual render receipt", visual_receipt_schema)):
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            return fail(f"{label} schema must use JSON Schema Draft 2020-12")
    ids = visual_catalog.get("template_ids", [])
    if visual_catalog.get("template_count") != 15 or len(ids) != 15 or len(set(ids)) != 15:
        return fail("visualization catalog must contain 14 Vega templates plus one optional Mermaid template")
    if len(list((root / "templates/visualizations").glob("*.vl.json"))) != 14:
        return fail("exactly 14 approved Vega-Lite template specs are required")
    if not (root / "templates/diagrams/D01_PROCESS_FLOW.mmd").is_file():
        return fail("optional D01 Mermaid source missing")
    if template.get("template_version") != "8.0" or client.get("properties", {}).get("template_version", {}).get("const") != "8.0":
        return fail("client template/schema must both be version 8.0")


    cap_items = capabilities.get("capabilities", [])
    cap_ids = {x.get("id") for x in cap_items if isinstance(x, dict) and x.get("id")}
    if not cap_ids or len(cap_ids) != len(cap_items):
        return fail("capability registry contains missing or duplicate IDs")
    for cap in cap_items:
        if cap.get("permission") not in {"public_read_only", "public_or_user_authorized", "user_authorized_private"}:
            return fail(f"invalid capability permission: {cap.get('id')}")
        if cap.get("unavailable_behavior") != "not_assessed":
            return fail(f"capability {cap.get('id')} must fall back to not_assessed")

    categories = registry.get("categories", {})
    if len(categories) != 6:
        return fail("measurement registry must contain six client categories")
    if round(sum(float(v.get("weight", 0)) for v in categories.values()), 6) != 100:
        return fail("category weights must sum to 100")
    anchors = registry.get("metric_score_scale", {})
    if anchors != {"strong": 100, "minor_gaps": 75, "mixed": 50, "weak": 25, "blocking": 0}:
        return fail("metric score anchors changed unexpectedly")

    sums = {cid: 0.0 for cid in categories}
    ids: set[str] = set()
    for m in registry.get("metrics", []):
        if not REQUIRED_METRIC_FIELDS <= set(m):
            return fail(f"metric {m.get('id')} missing machine-readable method fields")
        mid = m.get("id")
        if not mid or mid in ids:
            return fail(f"duplicate or missing metric id {mid}")
        ids.add(mid)
        cid = m.get("category")
        if cid not in sums:
            return fail(f"metric {mid} has unknown category {cid}")
        if m.get("capability_id") not in cap_ids:
            return fail(f"metric {mid} references unknown capability {m.get('capability_id')}")
        if m.get("max_evidence_grade") not in EVIDENCE_GRADES:
            return fail(f"metric {mid} has invalid max_evidence_grade")
        if not str(m.get("test_method", "")).strip() or not str(m.get("limitation", "")).strip():
            return fail(f"metric {mid} needs test_method and limitation")
        sums[cid] += float(m.get("weight", 0))
    bad = {k: v for k, v in sums.items() if round(v, 6) != 100}
    if bad:
        return fail(f"metric weights must sum to 100 per category: {bad}")
    if len(ids) != 48:
        return fail(f"expected 48 metrics, got {len(ids)}")
    legal_registry = json.loads((root / "assets/impressum-compliance-registry.v1.json").read_text(encoding="utf-8"))
    legal_ids = [x.get("id") for x in legal_registry.get("submetrics", [])]
    if legal_ids != [f"LEGAL-IMP-{i:02d}" for i in range(1, 12)]:
        return fail("impressum submetric registry must contain exact LEGAL-IMP-01..11")
    if sum(legal_registry.get("iles_dimensions", {}).values()) != 100:
        return fail("impressum ILES dimensions must sum to 100")
    for rel in ("schemas/impressum-evidence.schema.json", "schemas/impressum-compliance.schema.json"):
        json.loads((root / rel).read_text(encoding="utf-8"))
    print(f"PASS: schemas, capability registry and measurement registry ({len(ids)} metrics, {len(cap_ids)} capabilities; legal_submetrics={len(legal_ids)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
