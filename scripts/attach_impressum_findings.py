#!/usr/bin/env python3
"""Project a validated Impressum sidecar into one bounded customer-risk finding.

The sidecar remains the complete legal record. This projection intentionally
aggregates related legal submetrics so customer reporting gets one decision-useful
risk signal instead of multiple competing legal cards. Core score inputs are not
mutated.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from legal_customer_projection import resolve_projection

LABELS = {
    "LEGAL-IMP-01": "Anbieterkennzeichnung insgesamt",
    "LEGAL-IMP-02": "Betreiberidentit\u00e4t",
    "LEGAL-IMP-03": "geografische Gesch\u00e4ftsanschrift",
    "LEGAL-IMP-04": "elektronische Kontaktangaben",
    "LEGAL-IMP-05": "Rechtsform und Vertretung",
    "LEGAL-IMP-06": "Registerangaben",
    "LEGAL-IMP-07": "berufs- oder aufsichtsrechtliche Angaben",
    "LEGAL-IMP-08": "konditionale Identifikationsangaben",
    "LEGAL-IMP-09": "Auffindbarkeit der Anbieterangaben",
    "LEGAL-IMP-10": "widerspr\u00fcchliche Anbieterangaben",
    "LEGAL-IMP-11": "Zeitpunkt der Anbieterinformation",
}


def _result_map(sidecar: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in sidecar.get("results", []):
        if isinstance(row, dict) and row.get("metric_id"):
            out[str(row["metric_id"])] = row
    return out


def _has(sidecar: dict[str, Any], metric: str, defects: set[str] | None = None) -> bool:
    row = _result_map(sidecar).get(metric)
    if not row:
        return False
    if row.get("result_state") not in {"ASSESSED_DEFECT", "POSSIBLE_LEGAL_REVIEW", "CONFLICT"}:
        return False
    return defects is None or row.get("defect_type") in defects


def _customer_copy(sidecar: dict[str, Any], projection: dict[str, Any]) -> tuple[str, str, str, str]:
    refs = set(projection.get("legal_metric_refs", []))
    identity = "LEGAL-IMP-02" in refs
    address = "LEGAL-IMP-03" in refs
    claim = projection.get("claim_state")
    mandatory = projection.get("priority") in {"MANDATORY_CRITICAL", "MANDATORY_HIGH"}

    if identity and address:
        observation = "Betreiberidentit\u00e4t und Gesch\u00e4ftsanschrift waren \u00f6ffentlich nicht eindeutig auffindbar."
    elif identity:
        observation = "Die Betreiberidentit\u00e4t war auf den gepr\u00fcften \u00f6ffentlichen Seiten nicht eindeutig auffindbar."
    elif address:
        observation = "Eine geografische Gesch\u00e4ftsanschrift war auf den gepr\u00fcften \u00f6ffentlichen Seiten nicht eindeutig auffindbar."
    else:
        labels = [LABELS.get(ref, ref) for ref in projection.get("legal_metric_refs", [])[:3]]
        observation = "Bei den Anbieterangaben besteht ein konkreter Pr\u00fcfhinweis zu " + ", ".join(labels) + "."

    if claim == "ASSESSED_DEFECT":
        impact = "Der festgestellte Mangel betrifft zentrale Anbieter- oder Vertragspartnerinformationen und sollte kurzfristig rechtlich gekl\u00e4rt werden."
    elif claim == "CONFLICT":
        impact = "Widerspr\u00fcchliche Betreiberangaben erschweren die eindeutige Zuordnung des Vertragspartners und sollten kurzfristig gekl\u00e4rt werden."
    else:
        impact = "Je nach Sitz und Gesch\u00e4ftsmodell k\u00f6nnen zentrale Anbieterpflichten und die Vertragspartnertransparenz betroffen sein."

    if "LEGAL-IMP-08" in refs:
        action = "Anbieterangaben jetzt rechtlich pr\u00fcfen und korrigieren; steuerliche Identifikationsangaben zus\u00e4tzlich steuerlich pr\u00fcfen lassen."
    elif mandatory:
        action = "Anbieterkennzeichnung rechtlich pr\u00fcfen und korrigieren; Steuerangaben ggf. zus\u00e4tzlich steuerlich pr\u00fcfen lassen."
    else:
        action = "Anbieterangaben anhand der einschl\u00e4gigen Rechtslage pr\u00fcfen und erforderliche Angaben nachvollziehbar erg\u00e4nzen lassen."

    title = str(projection.get("warning_label") or "Rechtlicher Pr\u00fcfhinweis")
    return title, observation, impact, action


def finding_from(sidecar: dict[str, Any], idx: int) -> dict[str, Any] | None:
    projection = resolve_projection(sidecar)
    if projection.get("priority") == "INTERNAL_ONLY":
        return None
    title, observation, impact, action = _customer_copy(sidecar, projection)
    claim = projection.get("claim_state")
    if projection.get("priority") == "MANDATORY_CRITICAL" and claim == "ASSESSED_DEFECT":
        severity = "critical"
    elif projection.get("priority") in {"MANDATORY_CRITICAL", "MANDATORY_HIGH"}:
        severity = "high"
    else:
        severity = "medium"
    confidence = 4 if projection.get("required") else 3
    evidence_detail = ", ".join(projection.get("legal_metric_refs", [])) or "Impressum sidecar"
    return {
        "id": f"F-{idx:03d}",
        "category": "trust_privacy_content",
        "title": title,
        "severity": severity,
        "observation": observation,
        "evidence": [{
            "id": f"E-{900 + idx:03d}",
            "type": "legal_sidecar",
            "detail": evidence_detail + " from impressum-compliance.json; no direct score impact.",
            "method": "legal_customer_projection",
        }],
        "business_relevance": {
            "classification": "inference",
            "text": "Eindeutige Betreiberangaben reduzieren vermeidbare Vertrauens- und Rechtspr\u00fcfungsrisiken.",
        },
        "client_observation": observation,
        "client_impact": impact,
        "client_action": action,
        "recommendation": {
            "action": action,
            "owner": "Rechtsberatung + ggf. Steuerberatung",
            "horizon": "now" if projection.get("required") else "0_30_days",
            "acceptance_test": "Erneute Anbieterkennzeichnungs-Pr\u00fcfung ohne denselben belegten oder pr\u00fcfbed\u00fcrftigen Hinweis.",
        },
        "confidence": confidence,
        "metric_refs": list(projection.get("legal_metric_refs", [])),
        "customer_risk": {
            "domain": "provider_identification",
            "source": "impressum_compliance",
            "priority": projection.get("priority"),
            "claim_state": projection.get("claim_state"),
            "group": projection.get("group"),
            "warning_label": projection.get("warning_label"),
            "reason": projection.get("reason"),
            "legal_metric_refs": list(projection.get("legal_metric_refs", [])),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("diagnosis_report")
    ap.add_argument("sidecar")
    ap.add_argument("output")
    args = ap.parse_args()
    report = json.loads(Path(args.diagnosis_report).read_text(encoding="utf-8"))
    before = copy.deepcopy(report)
    side = json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
    allowed = {"findings", "sources", "limitations", "source_needed"}
    findings = report.setdefault("findings", [])

    # Idempotence: replace an earlier legal projection instead of stacking duplicates.
    findings[:] = [
        f for f in findings
        if not (
            isinstance(f, dict)
            and isinstance(f.get("customer_risk"), dict)
            and f["customer_risk"].get("source") == "impressum_compliance"
        )
    ]
    next_id = max([
        int(str(f.get("id", "F-000")).split("-")[-1])
        for f in findings
        if isinstance(f, dict) and str(f.get("id", "")).startswith("F-") and str(f.get("id", "")).split("-")[-1].isdigit()
    ] or [0]) + 1
    finding = finding_from(side, next_id)
    if finding is not None:
        findings.append(finding)

    if not any(s.get("id") == "SRC-LEGAL-IMP" for s in report.setdefault("sources", []) if isinstance(s, dict)):
        report["sources"].append({
            "id": "SRC-LEGAL-IMP",
            "type": "derived",
            "title": "Pixelkiez Impressum Compliance Sidecar",
            "location": "impressum-compliance.json",
            "purpose": "Non-core legal customer-risk projection",
        })
    limitation = "Legal findings are evidence-bounded review signals, not legal certification or penalty prediction."
    if limitation not in report.setdefault("limitations", []):
        report["limitations"].append(limitation)
    for item in side.get("source_needed", []):
        if item not in report.setdefault("source_needed", []):
            report["source_needed"].append(item)

    changed = {k for k in report if report.get(k) != before.get(k)}
    if not changed.issubset(allowed):
        raise SystemExit("FAIL: projection attempted forbidden top-level mutation: " + ",".join(sorted(changed - allowed)))
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    priority = resolve_projection(side).get("priority")
    print("PASS: impressum finding projection priority=" + str(priority) + " fields=" + ",".join(sorted(changed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
