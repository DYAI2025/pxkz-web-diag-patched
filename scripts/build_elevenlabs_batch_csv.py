#!/usr/bin/env python3
"""Build Pixelkiez ElevenLabs batch CSV v1.3 by default, preserving v1/v1.1/v1.2 compatibility."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_policy import derive_voice_evidence_class  # noqa: E402
from batch_contract import (  # noqa: E402
    DEFAULT_CONTRACT_VERSION, E164_RE, classification_counts, classification_names, context_allowed_names, contract_path, headers, has_classification_model, is_audit_owned, load_contract,
    production_gate_names, runtime_defaulted_names, runtime_required_names, serialize_value, sha256_file, specs_by_name, validate_csv_row,
)

DEFAULT_PROHIBITED_CLAIMS = [
    "Garantierte Umsatzwirkung",
    "Garantierter Rankingeffekt",
    "Nicht gemessene Conversionwirkung",
]
PRIORITY = {"critical": "HIGH", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}

SAFE_PROSPECT_SENTINEL = "NICHT_VERIFIZIERT"
SAFE_LEAD_SOURCE_SENTINEL = "NICHT_VERIFIZIERT"
SAFE_CONSULTANT_ROLE = "Pixelkiez Beratungsteam"

UNCERTAINTY_MARKERS = (
    "nicht gemessen", "nicht belastbar", "hypothese", "möglicherweise", "moeglicherweise", "könnte", "koennte", "kann relevant",
)


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def canonical_digest(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def iso_date(value: str) -> str:
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", text):
        return text[:10]
    raise ValueError(f"audit_date is not parseable as a calendar date: {value!r}")


def confidence_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return round(max(0.0, min(1.0, float(value) / 5.0)), 2)


def evidence_pointer(finding: dict[str, Any]) -> str:
    evidence = finding.get("evidence")
    if not isinstance(evidence, list) or not evidence or not isinstance(evidence[0], dict):
        return ""
    first = evidence[0]
    eid = str(first.get("id", "")).strip()
    url = str(first.get("url", "")).strip()
    if eid and url:
        return f"{eid}@{url}"
    return eid or url


def build_spoken(observation: str) -> str:
    clean = observation.strip().rstrip(".!?")
    return f"Bei unserem Website-Check ist uns aufgefallen: {clean}. Ist das für Sie relevant?"


def make_hook(finding: dict[str, Any], report: dict[str, Any] | None = None, allow_fallback: bool = True) -> dict[str, Any] | None:
    metric_refs = finding.get("metric_refs", []) if isinstance(finding.get("metric_refs"), list) else []
    if any(str(x).startswith("LEGAL-IMP-") for x in metric_refs):
        return None
    if finding.get("severity") == "positive":
        return None
    vh = finding.get("voice_hook")
    if vh is not None and not isinstance(vh, dict):
        return None
    if isinstance(vh, dict):
        evidence_class = str(vh.get("evidence_class", "")).strip()
        if report is not None:
            evidence_class = derive_voice_evidence_class(report, finding)
        if evidence_class == "UNKNOWN":
            return None
        spoken = str(vh.get("spoken", "")).strip()
        if evidence_class == "HYPOTHESIS" and spoken and not any(marker in spoken.lower() for marker in UNCERTAINTY_MARKERS):
            raise ValueError(f"finding {finding.get('id')} HYPOTHESIS spoken wording lacks an uncertainty marker")
        possible_relevance = str(vh.get("possible_relevance", "")).strip()
        prohibited = vh.get("prohibited_claims", [])
        if not isinstance(prohibited, list) or not all(isinstance(x, str) and x.strip() for x in prohibited):
            raise ValueError(f"finding {finding.get('id')} voice_hook.prohibited_claims must be a non-empty string list when supplied")
        if not prohibited:
            prohibited = DEFAULT_PROHIBITED_CLAIMS
        selector = vh.get("selector_score")
        if selector is not None and (isinstance(selector, bool) or not isinstance(selector, (int, float)) or not 0 <= float(selector) <= 1):
            raise ValueError(f"finding {finding.get('id')} selector_score must be 0..1")
        observation = str(vh.get("observation") or finding.get("observation") or finding.get("client_observation") or "").strip()
        if not spoken:
            spoken = build_spoken(str(finding.get("client_observation") or observation))
        if not possible_relevance:
            br = finding.get("business_relevance", {})
            possible_relevance = str(br.get("text", "")).strip() if isinstance(br, dict) else ""
        return {
            "id": str(finding.get("id", "")),
            "dimension": str(vh.get("dimension") or finding.get("category") or ""),
            "priority": str(vh.get("priority") or PRIORITY.get(str(finding.get("severity")), "LOW")),
            "evidence_class": evidence_class or "SUPPORTED_INFERENCE",
            "observation": observation,
            "evidence_pointer": str(vh.get("evidence_pointer") or evidence_pointer(finding)),
            "confidence": float(vh.get("confidence")) if isinstance(vh.get("confidence"), (int, float)) and not isinstance(vh.get("confidence"), bool) else confidence_number(finding.get("confidence")),
            "spoken": spoken,
            "possible_relevance": possible_relevance,
            "prohibited_claims": "|".join(prohibited),
            "selector_score": selector,
            "allow_as_hook_3": bool(vh.get("allow_as_hook_3", False)),
        }
    if not allow_fallback:
        return None
    pointer = evidence_pointer(finding)
    if not pointer:
        return None
    observation = str(finding.get("observation") or finding.get("client_observation") or "").strip()
    client_observation = str(finding.get("client_observation") or observation).strip()
    if not observation or not client_observation:
        return None
    br = finding.get("business_relevance", {})
    relevance = str(br.get("text", "")).strip() if isinstance(br, dict) else ""
    evidence_class = derive_voice_evidence_class(report, finding) if report is not None else "SUPPORTED_INFERENCE"
    spoken = build_spoken(client_observation)
    if evidence_class == "HYPOTHESIS":
        spoken = f"Möglicherweise relevant: {client_observation.rstrip('.!?')}. Ist das für Sie relevant?"
    if evidence_class == "UNKNOWN":
        return None
    return {
        "id": str(finding.get("id", "")),
        "dimension": str(finding.get("category", "")),
        "priority": PRIORITY.get(str(finding.get("severity")), "LOW"),
        "evidence_class": evidence_class,
        "observation": observation,
        "evidence_pointer": pointer,
        "confidence": confidence_number(finding.get("confidence")),
        "spoken": spoken,
        "possible_relevance": relevance,
        "prohibited_claims": "|".join(DEFAULT_PROHIBITED_CLAIMS),
        "selector_score": None,
        "allow_as_hook_3": False,
    }


def select_hooks(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        return []
    primary_secondary: list[dict[str, Any]] = []
    third: dict[str, Any] | None = None
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        hook = make_hook(finding, report)
        if not hook:
            continue
        if len(primary_secondary) < 2:
            primary_secondary.append(hook)
        elif hook.get("allow_as_hook_3"):
            third = hook
            break
    return primary_secondary + ([third] if third else [])


def assign(row: dict[str, Any], name: str, value: Any, *, conflict_is_error: bool = True) -> None:
    if value is None or value == "":
        return
    current = row.get(name)
    if current not in (None, "") and current != value:
        if conflict_is_error:
            raise ValueError(f"conflicting values for {name}: {current!r} vs {value!r}")
        return
    row[name] = value


def apply_public_business(report: dict[str, Any], row: dict[str, Any]) -> None:
    meta = report.get("meta", {})
    if not isinstance(meta, dict):
        raise ValueError("diagnosis report meta missing")
    business = report.get("public_business")
    if business is not None and not isinstance(business, dict):
        raise ValueError("public_business must be an object when present")
    business = business or {}
    display_name = str(business.get("display_name") or meta.get("customer_name") or "").strip()
    assign(row, "restaurant_name", display_name)
    assign(row, "prospect_company", display_name)
    assign(row, "customer_website", str(meta.get("audited_url") or "").strip())
    assign(row, "website_language", str(meta.get("website_language") or "").strip())
    assign(row, "phone_number", business.get("phone_number"))
    assign(row, "city", business.get("city"))
    assign(row, "district", business.get("district"))
    assign(row, "restaurant_category", business.get("business_category"))
    assign(row, "cuisine_type", business.get("cuisine_type"))
    contact = business.get("verified_contact")
    if contact is not None and not isinstance(contact, dict):
        raise ValueError("public_business.verified_contact must be an object")
    if isinstance(contact, dict):
        assign(row, "customer_name", contact.get("name"))
        assign(row, "customer_salutation", contact.get("salutation"))
        assign(row, "customer_role", contact.get("role"))
        assign(row, "prospect_role", contact.get("role"))


def apply_audit_fields(report: dict[str, Any], row: dict[str, Any]) -> None:
    meta = report.get("meta", {})
    score = report.get("score_summary", {})
    if not isinstance(meta, dict) or not isinstance(score, dict):
        raise ValueError("canonical report lacks meta/score_summary")
    audit_id = str(meta.get("audit_id") or "").strip()
    if not audit_id:
        audit_id = "AUD-PXK-" + canonical_digest(report)[:12].upper()
    assign(row, "audit_id", audit_id)
    assign(row, "audit_date", iso_date(str(meta.get("audit_date", ""))))
    assign(row, "audit_method_scope", str(meta.get("scope_summary") or "").strip())
    display = str(score.get("display_status", ""))
    if display == "FULL_SCORE" and isinstance(score.get("score"), (int, float)) and not isinstance(score.get("score"), bool):
        assign(row, "audit_overall_score", score.get("score"))
        assign(row, "audit_score_scale", "0-100")
        assign(row, "audit_score_status", "APPROVED_INTERNAL")
    elif display == "PARTIAL_SCORE":
        assign(row, "audit_score_status", "APPROVED_INTERNAL")
    else:
        assign(row, "audit_score_status", "NOT_USED")
    limits: list[str] = []
    for item in report.get("limitations", []) if isinstance(report.get("limitations"), list) else []:
        if isinstance(item, str) and item.strip():
            limits.append(item.strip())
    coverage = report.get("coverage", {})
    if isinstance(coverage, dict):
        for item in coverage.get("not_tested", []) if isinstance(coverage.get("not_tested"), list) else []:
            if isinstance(item, str) and item.strip() and item.strip() not in limits:
                limits.append(item.strip())
    assign(row, "audit_limitations", "; ".join(limits) if limits else "Keine zusätzlichen Limitations im validierten Audit dokumentiert.")
    findings = report.get("findings", [])
    if isinstance(findings, list):
        positive = next((f for f in findings if isinstance(f, dict) and f.get("severity") == "positive" and evidence_pointer(f)), None)
        if positive:
            assign(row, "audit_strength_1_observation", str(positive.get("client_observation") or positive.get("observation") or "").strip())
            assign(row, "audit_strength_1_evidence_pointer", evidence_pointer(positive))
            assign(row, "audit_strength_1_confidence", confidence_number(positive.get("confidence")))
    hooks = select_hooks(report)
    for idx, hook in enumerate(hooks[:3], 1):
        for suffix in ("id", "dimension", "priority", "evidence_class", "observation", "evidence_pointer", "confidence", "spoken", "possible_relevance", "prohibited_claims", "selector_score"):
            assign(row, f"audit_hook_{idx}_{suffix}", hook.get(suffix))


def validate_context(contract: dict[str, Any], context: dict[str, Any], digest: str) -> None:
    allowed = set(context_allowed_names(contract)) | {"_contract_digest", "_contract_version", "_allow_website_language_customer_language_default"}
    unknown = sorted(set(context) - allowed)
    if unknown:
        raise ValueError(f"batch_context has disallowed or audit-owned fields: {unknown}")
    if context.get("_contract_digest") not in (None, "", digest):
        raise ValueError("batch_context contract digest does not match selected bundled contract")
    if context.get("_contract_version") not in (None, "", contract.get("version")):
        raise ValueError("batch_context contract version does not match selected bundled contract")
    specs = specs_by_name(contract)
    for name, value in context.items():
        if name.startswith("_") or value is None or value == "":
            continue
        spec = specs[name]
        typ = str(spec.get("type"))
        if typ == "Boolean" and not isinstance(value, bool):
            raise ValueError(f"batch_context {name} must be Boolean")
        if typ == "Number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError(f"batch_context {name} must be Number")
        if typ == "String" and not isinstance(value, str):
            raise ValueError(f"batch_context {name} must be String")


def apply_context(contract: dict[str, Any], report: dict[str, Any], context: dict[str, Any], row: dict[str, Any]) -> None:
    meta = report.get("meta", {}) if isinstance(report.get("meta"), dict) else {}
    for name, value in context.items():
        if name.startswith("_") or value is None or value == "":
            continue
        spec = specs_by_name(contract)[name]
        if is_audit_owned(spec):
            raise ValueError(f"batch_context may not override audit-owned field {name}")
        if name == "customer_website" and meta.get("audited_url"):
            if normalize_url(str(value)) != normalize_url(str(meta.get("audited_url"))):
                raise ValueError("batch_context customer_website does not match audited_url")
        assign(row, name, value)
    if row.get("customer_locale") and not row.get("prospect_locale"):
        row["prospect_locale"] = row["customer_locale"]
    if row.get("customer_role") and not row.get("prospect_role"):
        row["prospect_role"] = row["customer_role"]
    if row.get("restaurant_name") and not row.get("prospect_company"):
        row["prospect_company"] = row["restaurant_name"]
    for alias, source in (("prospect_locale", "customer_locale"), ("prospect_role", "customer_role"), ("prospect_company", "restaurant_name")):
        if row.get(alias) and row.get(source) and row[alias] != row[source]:
            raise ValueError(f"alias mismatch: {alias} must equal {source}")
    if context.get("_allow_website_language_customer_language_default") is True and not row.get("customer_language") and row.get("website_language"):
        row["customer_language"] = row["website_language"]


def apply_phone_mirror(row: dict[str, Any]) -> None:
    phone = row.get("phone_number")
    recipient = row.get("recipient_number")
    if phone and recipient and phone != recipient:
        raise ValueError("phone_number and recipient_number differ")
    if phone and not recipient:
        row["recipient_number"] = phone
    elif recipient and not phone:
        row["phone_number"] = recipient
    if row.get("phone_number") and not E164_RE.fullmatch(str(row["phone_number"])):
        raise ValueError("phone_number must use E.164 format")


def apply_conversation_defaults(row: dict[str, Any]) -> None:
    defaults = {
        "call_stage": "PRECALL_GATE",
        "interest_level": "unknown",
        "confirmed_relevance": False,
        "meeting_readiness": "unknown",
        "opt_out": False,
        "needs_human": False,
    }
    for name, value in defaults.items():
        if row.get(name) in (None, ""):
            row[name] = value



def observed_agent_variables(contract: dict[str, Any]) -> list[str]:
    binding = contract.get("provider_binding", {}) if isinstance(contract.get("provider_binding"), dict) else {}
    names = binding.get("observed_agent_required_dynamic_variables_2026_08_28")
    if not isinstance(names, list):
        names = binding.get("required_dynamic_variables", [])
    return [str(name) for name in names if isinstance(name, str)]


def apply_provider_required_aliases(contract: dict[str, Any], report: dict[str, Any], row: dict[str, Any]) -> None:
    """Populate the exact non-empty Dynamic Variables required by the current ElevenLabs agent.

    This is a compatibility projection, not new authority. Fail-closed/sentinel values are
    intentionally non-empty so the provider variable gate can parse the row without turning
    unknown people, lead sources, or legal approval into fabricated facts.
    """
    if "company_name" not in row:
        return
    meta = report.get("meta", {}) if isinstance(report.get("meta"), dict) else {}
    company = str(row.get("prospect_company") or row.get("restaurant_name") or meta.get("customer_name") or "").strip()
    website = str(row.get("customer_website") or meta.get("audited_url") or "").strip()
    if not company or not website:
        raise ValueError("provider binding requires company_name/company_website from canonical audit evidence")
    if not row.get("company_name"): row["company_name"] = company
    if not row.get("company_website"): row["company_website"] = website

    if not row.get("prospect_name"):
        row["prospect_name"] = str(row.get("customer_name") or SAFE_PROSPECT_SENTINEL).strip() or SAFE_PROSPECT_SENTINEL
    if not row.get("prospect_salutation"):
        row["prospect_salutation"] = str(row.get("customer_salutation") or "Guten Tag").strip() or "Guten Tag"

    compliance = str(row.get("compliance_status") or "").strip()
    alias_compliance = str(row.get("call_compliance_status") or "").strip()
    if alias_compliance and compliance and alias_compliance != compliance:
        raise ValueError("call_compliance_status must equal compliance_status when both are supplied")
    if not alias_compliance:
        row["call_compliance_status"] = compliance if compliance in {"APPROVED", "BLOCKED", "LEGAL_REVIEW_REQUIRED"} else "LEGAL_REVIEW_REQUIRED"
    if not row.get("call_compliance_note"):
        if row["call_compliance_status"] == "APPROVED":
            row["call_compliance_note"] = "Externe Compliance-Freigabe aus batch_context; der Website-Audit trifft keine Rechtsentscheidung."
        elif row["call_compliance_status"] == "BLOCKED":
            row["call_compliance_note"] = "Externer Compliance-Status BLOCKED; kein Live-Call aus dieser Zeile."
        else:
            row["call_compliance_note"] = "Keine externe Call-Freigabe im Website-Audit; vor Live-Call prüfen."

    if not row.get("lead_source"):
        row["lead_source"] = str(row.get("lead_source_current") or SAFE_LEAD_SOURCE_SENTINEL).strip() or SAFE_LEAD_SOURCE_SENTINEL
    if not row.get("consultant_name"):
        row["consultant_name"] = SAFE_CONSULTANT_ROLE
    if not row.get("meeting_description"):
        offer = str(row.get("meeting_offer") or "").strip()
        row["meeting_description"] = (offer + ": unverbindliche Einordnung der Website-Analyse und möglicher nächster Schritte.") if offer else "Unverbindliche Einordnung der Website-Analyse und möglicher nächster Schritte."
    if not row.get("offer_process"):
        row["offer_process"] = "Website-Befund einordnen; bei Relevanz Beratungstermin; Umfang und Festpreis erst nach Diagnose festlegen."
    if not row.get("agency_name"):
        row["agency_name"] = "Pixelkiez"

    if not row.get("website_analysis_report"):
        audit_id = str(row.get("audit_id") or "").strip()
        score_status = str(row.get("audit_score_status") or "").strip()
        row["website_analysis_report"] = f"Pixelkiez Website-Analyse vorhanden; Audit-ID {audit_id}; Bericht pixelkiez-website-analysis.pdf; Score-Status {score_status}."

    if not row.get("verified_finding"):
        candidate = ""
        for idx in (1, 2, 3):
            if row.get(f"audit_hook_{idx}_evidence_class") == "VERIFIED_FACT" and row.get(f"audit_hook_{idx}_observation"):
                candidate = str(row[f"audit_hook_{idx}_observation"]).strip()
                break
        row["verified_finding"] = candidate or "Kein verifizierter Befund für das Gespräch freigegeben."

    provider_names = observed_agent_variables(contract)
    missing = [name for name in provider_names if not str(row.get(name) or "").strip()]
    if missing:
        raise ValueError("observed current-agent variables remained empty after safe compiler defaults: " + ", ".join(missing))


def validation_payload(contract: dict[str, Any], contract_digest: str, report_path: Path, context_path: Path | None, result: dict[str, Any]) -> dict[str, Any]:
    values = result.get("values", {})
    specs = specs_by_name(contract)
    classified = has_classification_model(contract)
    provider_names = [n for n in observed_agent_variables(contract) if n in values]
    provider_missing = [n for n in provider_names if not str(values.get(n, "")).strip()]
    provider_gate = "PASS" if provider_names and not provider_missing else ("NOT_APPLICABLE" if not provider_names else "BLOCKED")

    missing_runtime_required = result.get("missing_runtime_required_fields", [])
    missing_runtime_defaulted = result.get("missing_runtime_defaulted_fields", [])
    missing_production = result.get("missing_production_gate_fields", [])
    missing_required = result.get("missing_required_fields", [])
    grouped: dict[str, list[str]] = {}
    for name in missing_production if classified else missing_required:
        source = str(specs[name].get("source", "UNKNOWN"))
        grouped.setdefault(source, []).append(name)

    compliance = values.get("compliance_status", "")
    dnc = values.get("do_not_contact", "")
    recording = values.get("recording_status", "")
    production_reasons: list[str] = []
    if missing_production:
        production_reasons.append("PRODUCTION_GATE_ONLY fields missing")
    if compliance != "APPROVED":
        production_reasons.append(f"compliance_status={compliance or 'MISSING'}")
    if dnc != "false":
        production_reasons.append(f"do_not_contact={dnc or 'MISSING'}")
    if recording not in {"OFF", "APPROVED"}:
        production_reasons.append(f"recording_status={recording or 'MISSING'}")

    upload_ready = bool(result.get("elevenlabs_upload_ready", result.get("batch_ready", False)))
    production_gate = bool(result.get("production_prerequisite_gate_passed", result.get("outreach_policy_gate_passed", False)))
    payload = {
        "contract_version": contract.get("version"),
        "contract_sha256": contract_digest,
        "source_report_sha256": sha256_file(report_path),
        "batch_context_sha256": sha256_file(context_path) if context_path else None,
        "field_count": len(headers(contract)),
        "export_status": "AUDIT_EXPORT_COMPLETE" if not result["errors"] else "INVALID",
        "batch_status": "BATCH_READY" if upload_ready else "NOT_BATCH_READY",
        "batch_status_semantics": "BACKWARD_COMPATIBILITY_ALIAS_OF_ELEVENLABS_UPLOAD_STATUS" if classified else "LEGACY_SELECTED_CONTRACT_REQUIREDNESS",
        "elevenlabs_upload_status": "EL_UPLOAD_READY" if upload_ready else "EL_UPLOAD_BLOCKED",
        "production_prerequisite_gate": "PASS" if production_gate else "BLOCKED",
        "production_prerequisite_gate_reasons": [] if production_gate else production_reasons,
        "outreach_policy_gate": "PASS" if production_gate else "BLOCKED",
        "outreach_policy_gate_reasons": [] if production_gate else production_reasons,
        "live_call_production_status": "NOT_ASSESSED",
        "elevenlabs_agent_variable_gate": provider_gate,
        "elevenlabs_agent_required_dynamic_variables": provider_names,
        "missing_elevenlabs_agent_required_dynamic_variables": provider_missing,
        "missing_required_fields": missing_required,
        "missing_runtime_required_fields": missing_runtime_required,
        "missing_runtime_defaulted_fields": missing_runtime_defaulted,
        "missing_production_gate_fields": missing_production,
        "missing_required_by_authority": grouped,
        "missing_recommended_fields": result.get("missing_recommended_fields", []),
        "optional_blank_fields": result.get("optional_blank_fields", []),
        "internal_blank_fields": result.get("internal_blank_fields", []),
        "validation_errors": result["errors"],
        "does_not_prove": [
            "legal approval for a concrete outbound campaign",
            "ElevenLabs upload success or provider behavior",
            "live-call readiness, conversation quality, booking success, or business outcome",
        ],
    }
    if classified:
        payload["classification_model"] = contract.get("classification_model")
        payload["classification_counts"] = classification_counts(contract)
        payload["field_classifications"] = {name: specs[name].get("classification") for name in headers(contract)}
        payload["elevenlabs_runtime_required_fields"] = runtime_required_names(contract)
        payload["elevenlabs_runtime_defaulted_fields"] = runtime_defaulted_names(contract)
        payload["production_gate_only_fields"] = production_gate_names(contract)
        payload["optional_fields"] = classification_names(contract, "OPTIONAL")
        payload["internal_record_fields"] = classification_names(contract, "INTERNAL_RECORD")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagnosis_report")
    parser.add_argument("output_csv")
    parser.add_argument("--batch-context")
    parser.add_argument("--validation-out")
    parser.add_argument("--contract-version", choices=["v1", "v1.1", "v1.2", "v1.3"], default=DEFAULT_CONTRACT_VERSION, help="Default v1.3 five-class 96-field export; v1/v1.1/v1.2 remain explicit compatibility modes.")
    args = parser.parse_args()
    report_path = Path(args.diagnosis_report).resolve()
    out_path = Path(args.output_csv).resolve()
    context_path = Path(args.batch_context).resolve() if args.batch_context else None
    validation_path = Path(args.validation_out).resolve() if args.validation_out else out_path.with_suffix(".validation.json")
    try:
        report = load_object(report_path)
        selected_contract_path = contract_path(args.contract_version, Path(__file__).resolve().parents[1])
        contract = load_contract(selected_contract_path)
        digest = sha256_file(selected_contract_path)
        context = load_object(context_path) if context_path else {}
        validate_context(contract, context, digest)
        row: dict[str, Any] = {name: None for name in headers(contract)}
        apply_public_business(report, row)
        apply_audit_fields(report, row)
        apply_context(contract, report, context, row)
        apply_phone_mirror(row)
        apply_conversation_defaults(row)
        apply_provider_required_aliases(contract, report, row)
        spec_map = specs_by_name(contract)
        serialized = [serialize_value(row[name], str(spec_map[name].get("type"))) for name in headers(contract)]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            writer.writerow(headers(contract))
            writer.writerow(serialized)
        result = validate_csv_row(contract, headers(contract), serialized)
        result["values"] = dict(zip(headers(contract), serialized))
        payload = validation_payload(contract, digest, report_path, context_path, result)
        validation_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if result["errors"]:
            return fail("; ".join(result["errors"]))
        print(
            f"PASS: wrote {out_path} fields={len(headers(contract))} export={payload['export_status']} "
            f"upload={payload['elevenlabs_upload_status']} production_gate={payload['production_prerequisite_gate']} contract={digest}"
        )
        if payload["missing_required_fields"]:
            print("MISSING_REQUIRED: " + ", ".join(payload["missing_required_fields"]))
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
