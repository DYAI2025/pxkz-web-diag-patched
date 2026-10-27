#!/usr/bin/env python3
"""VC03_DIAGNOSTIC evidence route: when a Vibe-Check #03 observation may become a customer lever.

The VC03 block stays non-scoring. A finding derived from it is admissible only if
every cited observation resolves to an OBSERVED row of the same run and page, the
versioned defect rule still holds on those values, exactly one measurement source
reports the metric, and the finding carries a business mechanism, an action and a
retest. Anything else is rejected with a machine-readable reason and never counted
as a weakness.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "assets" / "vibecheck03-customer-admission-rules.v1.json"
CATALOG_PATH = ROOT / "assets" / "vibecheck03.check-catalog.v1.json"
EVIDENCE_TYPE = "vibecheck03_diagnostic"
ROUTE = "VC03_DIAGNOSTIC"
SOURCE_AUTHORITY = "STANDALONE_OFFLINE"
ALLOWED_SEVERITIES = {"medium", "low"}

# Outcome, benchmark and legal-certainty claims VC03 markup evidence can never support.
FORBIDDEN_CLAIM_RX = re.compile(
    r"\d+\s*%|\bprozent\b|umsatz|verlier(?:t|en)\b|conversion|rechtswidrig|verst(?:ö|oe)(?:ß|ss)t|abmahn|"
    r"google\s+(?:straft|klassifiziert|wertet)|whatsapp\s+zeigt|garantiert|ranking|branchenschnitt|wettbewerber",
    re.I,
)


def load_rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


DEFAULT_PORTS = {"http": 80, "https": 443}


def page_key(url: str) -> tuple[str, str, int | None, str, str] | None:
    """Exact page identity: scheme, host, effective port, path, query (fragment ignored)."""
    try:
        parts = urlsplit(str(url or ""))
        port = parts.port
    except ValueError:
        return None
    scheme, host = parts.scheme.lower(), (parts.hostname or "").lower().rstrip(".")
    if not scheme or not host:
        return None
    return scheme, host, port or DEFAULT_PORTS.get(scheme), parts.path or "/", parts.query


def audited_pages(report: dict[str, Any]) -> set[tuple[str, str, int | None, str, str]]:
    meta = report.get("meta", {}) if isinstance(report.get("meta"), dict) else {}
    coverage = report.get("coverage", {}) if isinstance(report.get("coverage"), dict) else {}
    urls = [meta.get("audited_url")] + [p.get("url") for p in coverage.get("sampled_pages", []) if isinstance(p, dict)]
    return {k for k in map(page_key, urls) if k}


def metric_types() -> dict[str, str]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {m["metric_id"]: m["type"] for c in catalog["checks"] for m in c["metrics"]}


def value_matches_type(value: Any, kind: str) -> bool:
    if kind == "BOOLEAN":
        return type(value) is bool
    if kind == "INTEGER":
        return type(value) is int and value >= 0
    return False


def is_vc03_finding(finding: dict[str, Any]) -> bool:
    return any(isinstance(e, dict) and e.get("type") == EVIDENCE_TYPE for e in finding.get("evidence", []) or [])


def evidence_ref_of(item: dict[str, Any]) -> str:
    return str(item.get("detail", "")).split(" = ", 1)[0].strip()


def detail_value_of(item: dict[str, Any]) -> str | None:
    parts = str(item.get("detail", "")).split(" = ", 1)
    return parts[1].strip() if len(parts) == 2 else None


def render_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def condition_holds(condition: dict[str, Any], values: dict[str, Any]) -> bool:
    def one(term: dict[str, Any]) -> bool:
        if term["metric"] not in values:
            return False
        value = values[term["metric"]]
        if "eq" in term:
            return type(value) is type(term["eq"]) and value == term["eq"]
        if "in" in term:
            return type(value) is int and value in term["in"]
        if "gt" in term:
            return type(value) is int and value > term["gt"]
        if "lte_metric" in term:
            other = values.get(term["lte_metric"])
            return type(value) is int and type(other) is int and value <= other
        return False

    if "all" in condition:
        return all(one(t) for t in condition["all"])
    if "any" in condition:
        return any(one(t) for t in condition["any"])
    return False


def block_errors(report: dict[str, Any], block: Any) -> list[str]:
    """Binding of the VC03 block to the audited site, the analysis run and one source authority."""
    if not isinstance(block, dict):
        return ["VC03_BLOCK_MISSING"]
    errors: list[str] = []
    if block.get("source_authority") != SOURCE_AUTHORITY or block.get("score_effect") != "NONE":
        errors.append("VC03_BLOCK_AUTHORITY")
    meta = report.get("meta", {}) if isinstance(report.get("meta"), dict) else {}
    # The page must be one the analysis itself audited (same port, path and query).
    if page_key(block.get("page_url", "")) not in audited_pages(report):
        errors.append("VC03_BLOCK_PAGE_NOT_AUDITED_SITE")
    # Without an analysis run id there is nothing to bind the VC03 run to: fail closed.
    if not meta.get("audit_id"):
        errors.append("VC03_RUN_UNBOUND")
    elif meta.get("audit_id") != block.get("run_id"):
        errors.append("VC03_RUN_MISMATCH")
    types = metric_types()
    for m in block.get("metrics", []):
        if isinstance(m, dict) and m.get("status") == "OBSERVED" and not value_matches_type(m.get("value"), types.get(str(m.get("metric_id")), "")):
            errors.append("VC03_VALUE_TYPE_INVALID")
            break
    metric_ids = [m.get("metric_id") for m in block.get("metrics", []) if isinstance(m, dict)]
    evidence_ids = [e.get("id") for e in block.get("evidence", []) if isinstance(e, dict)]
    if len(metric_ids) != len(set(metric_ids)) or len(evidence_ids) != len(set(evidence_ids)):
        errors.append("VC03_BLOCK_CONFLICT")
    return errors


def observed_rows(block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence_ids = {e.get("id") for e in block.get("evidence", []) if isinstance(e, dict)}
    return {
        str(m["metric_id"]): m for m in block.get("metrics", [])
        if isinstance(m, dict) and m.get("status") == "OBSERVED" and m.get("evidence_ref") in evidence_ids
        and m.get("run_id") == block.get("run_id") and m.get("page_url") == block.get("page_url")
    }


def other_source_metrics(report: dict[str, Any]) -> set[str]:
    """Metric ids reported by a second measurement source (never auto-merged with VC03)."""
    enrichment = report.get("measurement_enrichment")
    rows = enrichment.get("metrics", []) if isinstance(enrichment, dict) else []
    return {str(r.get("metric_id") or r.get("id")) for r in rows if isinstance(r, dict)}


def evaluate_route(report: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    """Return {reasons, rule_id, vc03_refs}; empty reasons means admissible via VC03_DIAGNOSTIC."""
    block = report.get("vibecheck03")
    reasons = block_errors(report, block)
    if "VC03_BLOCK_MISSING" in reasons:
        return {"reasons": reasons, "rule_id": None, "vc03_refs": []}
    rows = observed_rows(block)
    by_ref = {r["evidence_ref"]: r for r in rows.values()}
    items = [e for e in finding.get("evidence", []) if isinstance(e, dict) and e.get("type") == EVIDENCE_TYPE]
    refs = [evidence_ref_of(e) for e in items]

    cited: dict[str, dict[str, Any]] = {}
    for item, ref in zip(items, refs):
        row = by_ref.get(ref)
        if row is None:
            reasons.append("VC03_EVIDENCE_UNRESOLVED")
            continue
        if item.get("url") != block.get("page_url"):
            reasons.append("VC03_PAGE_MISMATCH")
        if detail_value_of(item) != render_value(row["value"]):
            reasons.append("VC03_VALUE_CONFLICT")
        cited[row["metric_id"]] = row
    if len(set(refs)) != len(refs):
        reasons.append("VC03_DUPLICATE_OBSERVATION")

    rule = next((r for r in load_rules()["rules"] if r.get("customer_admission") and set(r["evidence_metrics"]) == set(cited)), None)
    if rule is None:
        reasons.append("VC03_NO_MATCHING_RULE")
    elif not condition_holds(rule["condition"], {k: v["value"] for k, v in cited.items()}):
        reasons.append("VC03_RULE_NOT_SATISFIED")

    if set(cited) & other_source_metrics(report):
        reasons.append("VC03_SOURCE_CONFLICT")
    for other in report.get("findings", []):
        if other is finding or not isinstance(other, dict) or other.get("id") == finding.get("id"):
            continue
        if set(refs) & {evidence_ref_of(e) for e in other.get("evidence", []) if isinstance(e, dict) and e.get("type") == EVIDENCE_TYPE}:
            reasons.append("VC03_DUPLICATE_OBSERVATION")
            break
    if finding.get("metric_refs"):
        reasons.append("VC03_CORE_METRIC_REFS_FORBIDDEN")
    if finding.get("customer_risk"):
        reasons.append("VC03_CUSTOMER_RISK_FORBIDDEN")
    if finding.get("severity") not in ALLOWED_SEVERITIES:
        reasons.append("VC03_SEVERITY_CAP")
    if not str((finding.get("recommendation") or {}).get("acceptance_test") or "").strip():
        reasons.append("VC03_NO_RETEST")
    if not str((finding.get("business_relevance") or {}).get("text") or "").strip():
        reasons.append("VC03_NO_BUSINESS_MECHANISM")
    claim_surface = " ".join(str(finding.get(k) or "") for k in ("title", "client_observation", "client_impact", "client_action"))
    claim_surface += " " + str((finding.get("business_relevance") or {}).get("text") or "")
    if FORBIDDEN_CLAIM_RX.search(claim_surface):
        reasons.append("VC03_FORBIDDEN_CLAIM")
    return {"reasons": list(dict.fromkeys(reasons)), "rule_id": rule["rule_id"] if rule else None, "vc03_refs": refs}


def triggered_rules(block: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, dict[str, Any]]]]:
    rows = observed_rows(block)
    out = []
    for rule in load_rules()["rules"]:
        if all(m in rows for m in rule["evidence_metrics"]) and condition_holds(
            rule["condition"], {m: rows[m]["value"] for m in rule["evidence_metrics"]}
        ):
            out.append((rule, {m: rows[m] for m in rule["evidence_metrics"]}))
    return out


def admission_summary(report: dict[str, Any]) -> dict[str, Any] | None:
    """Internal-only record: what was admitted, what stayed internal and why, what was not assessed."""
    block = report.get("vibecheck03")
    if not isinstance(block, dict):
        return None
    rows = observed_rows(block)
    fired = {rule["rule_id"] for rule, _ in triggered_rules(block)}
    from client_story import select_client_levers  # local import: client_story depends on this module

    selected = {str(f.get("id")) for f in select_client_levers(report)}
    findings = [f for f in report.get("findings", []) if isinstance(f, dict) and is_vc03_finding(f)]
    by_rule: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        result = evaluate_route(report, f)
        by_rule.setdefault(str(result["rule_id"]), []).append({
            "finding_id": f.get("id"), "reasons": result["reasons"],
            "selected_in_default_customer_levers": str(f.get("id")) in selected,
        })
    entries = []
    for rule in load_rules()["rules"]:
        rid = rule["rule_id"]
        missing = [m for m in rule["evidence_metrics"] if m not in rows]
        if rule.get("customer_admission") is False:
            status = rule["internal_reason"] if rid in fired else ("NOT_ASSESSED" if len(missing) == len(rule["evidence_metrics"]) else "NOT_TRIGGERED")
        elif rid in by_rule:
            status = "ELIGIBLE" if all(not x["reasons"] for x in by_rule[rid]) else "REJECTED"
        elif missing:
            status = "NOT_ASSESSED"
        else:
            status = "NOT_TRIGGERED" if rid not in fired else "TRIGGERED_NOT_ATTACHED"
        entries.append({"rule_id": rid, "check_id": rule["check_id"], "status": status,
                        "not_assessed_metrics": missing, "findings": by_rule.get(rid, [])})
    orphan = by_rule.get("None", [])
    return {
        "route": ROUTE, "rules_version": load_rules()["version"], "run_id": block.get("run_id"),
        "page_url": block.get("page_url"), "binding_errors": block_errors(report, block),
        "score_effect": "NONE", "rules": entries, "unmatched_findings": orphan,
        "not_assessed_is_negative": False,
    }
