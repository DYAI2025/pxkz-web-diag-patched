#!/usr/bin/env python3
"""Build the complete internal Pixelkiez analysis report from the canonical scored audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from business_value import finding_business_record, metric_business_interpretation
from visual_eligibility import classify as classify_visual
from vibecheck03_admission import admission_summary


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interpretation(metric: dict[str, Any], label: str) -> str:
    if not metric.get("applicable", True):
        return f"{label} ist für diesen Audit als nicht anwendbar dokumentiert; daraus wird keine positive oder negative Bewertung abgeleitet."
    mclass = str(metric.get("measurement_class") or "")
    status = str(metric.get("status") or "")
    if mclass == "not_assessed" or status == "not_assessed":
        return f"{label} wurde nicht belastbar erhoben. Der Bericht behandelt die Lücke als offene Evidenz und nicht als Wert null."
    score = metric.get("score")
    value = metric.get("value")
    unit = str(metric.get("unit") or "").strip()
    value_text = "nicht numerisch" if value in (None, "") else f"{value}{(' ' + unit) if unit else ''}"
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        if score >= 80:
            level = "starke Ausprägung"
        elif score >= 60:
            level = "solide Ausprägung mit möglichem Verbesserungsbedarf"
        elif score >= 40:
            level = "erkennbare Schwäche"
        else:
            level = "deutliche Schwäche"
        return f"Der dokumentierte Wert für {label} ist {value_text}; im Pixelkiez Bewertungsmodell entspricht das {score:g}/100 und wird als {level} eingeordnet."
    return f"Für {label} ist der Wert {value_text} dokumentiert, aber kein normalisierter Score freigegeben. Die Einordnung bleibt deshalb deskriptiv."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report")
    ap.add_argument("output")
    ap.add_argument("--registry", default=None)
    args = ap.parse_args()
    report_path = Path(args.report).resolve()
    output = Path(args.output).resolve()
    root = Path(__file__).resolve().parents[1]
    registry_path = Path(args.registry).resolve() if args.registry else root / "assets/measurement-registry.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        reg = {str(m["id"]): m for m in registry.get("metrics", [])}
        findings = [x for x in report.get("findings", []) if isinstance(x, dict)]
        finding_map = {str(x.get("id")): x for x in findings if x.get("id")}
        metric_findings: dict[str, list[str]] = {}
        recommendations: list[dict[str, Any]] = []
        for finding in findings:
            fid = str(finding.get("id"))
            refs = [str(x) for x in finding.get("metric_refs", []) if str(x)]
            for ref in refs:
                metric_findings.setdefault(ref, []).append(fid)
            rec = finding.get("recommendation") if isinstance(finding.get("recommendation"), dict) else {}
            recommendations.append({
                "id": f"REC-{fid}",
                "finding_id": fid,
                "metric_refs": refs,
                "severity": finding.get("severity"),
                "action": str(rec.get("action") or finding.get("client_action") or "NO_ACTION"),
                "owner": str(rec.get("owner") or "MISSING_OWNER"),
                "horizon": str(rec.get("horizon") or "MISSING_HORIZON"),
                "acceptance_test": str(rec.get("acceptance_test") or "MISSING_ACCEPTANCE_TEST"),
                "business_relevance": finding.get("business_relevance", {}),
            })
        metric_rows: list[dict[str, Any]] = []
        for metric in report.get("metrics", []):
            mid = str(metric.get("id"))
            definition = reg.get(mid, {})
            label = str(definition.get("label_de") or mid)
            linked = metric_findings.get(mid, [])
            mclass = str(metric.get("measurement_class") or "")
            action_state = "NOT_ASSESSED" if mclass == "not_assessed" else ("LINKED_ACTION" if linked else "NO_ACTION")
            business = metric_business_interpretation(metric, label, str(definition.get("category") or "unmapped"))
            metric_rows.append({
                "id": mid,
                "category": str(definition.get("category") or "unmapped"),
                "label": label,
                "applicable": bool(metric.get("applicable", True)),
                "measurement_class": mclass,
                "evidence_grade": str(metric.get("evidence_grade") or ""),
                "status": metric.get("status"),
                "value": metric.get("value"),
                "unit": metric.get("unit"),
                "score": metric.get("score"),
                "metric_weight": float(definition.get("weight", 0)),
                "category_weight": float((registry.get("categories", {}).get(str(definition.get("category") or ""), {}) or {}).get("weight", 0)),
                "weighted_contribution": (round(float(metric.get("score")) * float(definition.get("weight", 0)) / 100.0, 6) if isinstance(metric.get("score"), (int, float)) and not isinstance(metric.get("score"), bool) else None),
                "score_admitted": bool(metric.get("applicable", True) and mclass in {"measured", "observed"} and isinstance(metric.get("score"), (int, float)) and not isinstance(metric.get("score"), bool)),
                "confidence": metric.get("confidence"),
                "source_or_method": str(metric.get("source_or_method") or definition.get("test_method") or "MISSING_METHOD"),
                "threshold_source": metric.get("threshold_source"),
                "evidence_refs": [str(x) for x in metric.get("evidence_refs", [])],
                "does_not_prove": str(metric.get("does_not_prove") or definition.get("limitation") or "MISSING_LIMITATION"),
                "interpretation": interpretation(metric, label),
                "business_question": business["business_question"],
                "business_effect_channel": business["business_effect_channel"],
                "business_interpretation": business["business_interpretation"],
                "visual_decision": classify_visual({"value": metric.get("value"), "status": metric.get("status")}),
                "action_state": action_state,
                "recommendation_refs": [f"REC-{fid}" for fid in linked],
            })
        score_summary = report.get("score_summary", {}) if isinstance(report.get("score_summary"), dict) else {}
        score_categories = {str(x.get("category")): x for x in score_summary.get("category_scores", []) if isinstance(x, dict)}
        category_order = [str(x.get("id")) for x in registry.get("categories", []) if isinstance(x, dict)]
        if not category_order:
            category_order = list(dict.fromkeys(x["category"] for x in metric_rows))
        categories = []
        for category in category_order:
            members = [x for x in metric_rows if x["category"] == category]
            if not members:
                continue
            c = score_categories.get(category, {})
            admitted_members = [x for x in members if x.get("score_admitted")]
            scored_metric_weight = sum(float(x.get("metric_weight", 0)) for x in admitted_members)
            weighted_score_numerator = sum(float(x.get("score", 0)) * float(x.get("metric_weight", 0)) for x in admitted_members)
            category_weight = float((registry.get("categories", {}).get(category, {}) or {}).get("weight", 0))
            categories.append({
                "category": category,
                "label": c.get("label") or category,
                "score": c.get("score"),
                "coverage": c.get("coverage_percent"),
                "status": "NOT_SCORED" if c.get("score") is None else ("STRONG" if c["score"] >= 80 else "SOLID" if c["score"] >= 60 else "NEEDS_ACTION"),
                "metric_count": len(members),
                "category_weight": category_weight,
                "scored_metric_weight": round(scored_metric_weight, 6),
                "weighted_score_numerator": round(weighted_score_numerator, 6),
                "category_weighted_contribution": (round(float(c.get("score")) * category_weight / 100.0, 6) if isinstance(c.get("score"), (int, float)) and not isinstance(c.get("score"), bool) else None),
                "aggregation_rule": "sum(metric_score * metric_weight) / sum(metric_weight for score-admitted metrics)",
            })
        business_implications = [finding_business_record(f) for f in findings]
        payload = {
            "schema_version": "1.2",
            "source_report_sha256": sha(report_path),
            "meta": report.get("meta", {}),
            "business_profile": {
                "company": report.get("meta", {}).get("customer_name"),
                "website": report.get("meta", {}).get("audited_url"),
                "market": report.get("meta", {}).get("market"),
                "language": report.get("meta", {}).get("language"),
            },
            "executive_summary": report.get("executive_summary", {}),
            "score_summary": score_summary,
            "categories": categories,
            "metrics": metric_rows,
            "findings": findings,
            "business_implications": business_implications,
            "recommendations": recommendations,
            "benchmarks": [report.get("benchmark_data")] if isinstance(report.get("benchmark_data"), dict) else [],
            "ranking_observations": [
                {"query": x.get("query"), "position": x.get("value"), "device": x.get("device"), "location": x.get("location"), "observed_at": x.get("observed_at"), "evidence_ref": x.get("evidence_ref")}
                for x in ((report.get("measurement_enrichment") or {}).get("metrics", []) if isinstance(report.get("measurement_enrichment"), dict) else [])
                if isinstance(x, dict) and x.get("id") == "SERP_CURRENT_POSITION" and x.get("status") in {"MEASURED", "OBSERVED"}
            ],
            "visual_candidates": [m["visual_decision"] | {"metric_id": m["id"]} for m in metric_rows],
            "measurement_enrichment": report.get("measurement_enrichment"),
            "vibecheck03": report.get("vibecheck03"),
            "roadmap": report.get("roadmap", []),
            "coverage": report.get("coverage", {}),
            "sources": report.get("sources", []),
            "limitations": report.get("limitations", []),
            "missing": report.get("missing", []),
            "source_needed": report.get("source_needed", []),
        }
        if isinstance(report.get("vibecheck03"), dict):
            # Internal-only: which VC03 observations reached the customer route, which stayed internal and why.
            payload["vibecheck03_admission"] = admission_summary(report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: internal analysis report metrics={len(metric_rows)} findings={len(findings)} recommendations={len(recommendations)}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
