#!/usr/bin/env python3
"""Compute the transparent Pixelkiez quality score and coverage from metric records."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_DIR / "assets" / "measurement-registry.json"
CAPABILITY_PATH = SKILL_DIR / "assets" / "capability-registry.json"
GRADE_RANK = {f"E{i}": i for i in range(1, 9)}
SCOREABLE_CLASSES = {"measured", "observed"}


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def interpretation(score: int | None) -> str:
    if score is None:
        return "Für eine belastbare Gesamtzahl fehlen noch Messungen"
    if score < 40:
        return "Grundlegender Handlungsbedarf"
    if score < 60:
        return "Deutlicher Verbesserungsbedarf"
    if score < 75:
        return "Solide Basis, klare Hebel"
    if score < 90:
        return "Stark mit gezielten Lücken"
    return "Sehr stark im geprüften Umfang"


def confidence_label(coverage: float, e6_weight: float, scored_weight: float) -> str:
    e6_share = (e6_weight / scored_weight) if scored_weight else 1.0
    if coverage >= 0.80 and e6_share < 0.50:
        return "HIGH"
    if coverage >= 0.50:
        return "MEDIUM"
    return "LOW"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return fail("usage: compute_score.py <input-report.json> <output-report.json>")

    source = Path(argv[1])
    output = Path(argv[2])
    try:
        report = load_json(source)
        registry = load_json(REGISTRY_PATH)
        capability_registry = load_json(CAPABILITY_PATH)
    except Exception as exc:
        return fail(str(exc))

    categories = registry.get("categories", {})
    metric_defs = registry.get("metrics", [])
    if not isinstance(categories, dict) or not isinstance(metric_defs, list):
        return fail("invalid measurement registry")

    category_weight_sum = sum(float(v.get("weight", 0)) for v in categories.values() if isinstance(v, dict))
    if round(category_weight_sum, 6) != 100:
        return fail(f"category weights must sum to 100, got {category_weight_sum}")

    defs_by_id: dict[str, dict[str, Any]] = {}
    metric_weight_sums: dict[str, float] = {cid: 0.0 for cid in categories}
    for item in metric_defs:
        if not isinstance(item, dict) or not item.get("id"):
            return fail("registry metric missing id")
        mid = str(item["id"])
        if mid in defs_by_id:
            return fail(f"duplicate registry metric {mid}")
        defs_by_id[mid] = item
        cid = item.get("category")
        if cid not in categories:
            return fail(f"registry metric {mid} has unknown category {cid}")
        metric_weight_sums[cid] += float(item.get("weight", 0))

    for cid, total in metric_weight_sums.items():
        if round(total, 6) != 100:
            return fail(f"metric weights for {cid} must sum to 100, got {total}")

    report_metrics = report.get("metrics", [])
    if not isinstance(report_metrics, list):
        return fail("report.metrics must be a list")
    report_by_id: dict[str, dict[str, Any]] = {}
    for item in report_metrics:
        if not isinstance(item, dict):
            return fail("every report metric must be an object")
        mid = str(item.get("id", ""))
        if mid not in defs_by_id:
            return fail(f"report metric {mid!r} not found in registry")
        if mid in report_by_id:
            return fail(f"duplicate report metric {mid}")
        report_by_id[mid] = item

    missing_metric_ids = sorted(set(defs_by_id) - set(report_by_id))
    if missing_metric_ids:
        return fail("report must contain every registry metric row; missing: " + ", ".join(missing_metric_ids))

    cap_defs = {c.get("id") for c in capability_registry.get("capabilities", []) if isinstance(c, dict)}
    cap_rows = report.get("coverage", {}).get("capabilities", [])
    cap_status: dict[str, str] = {}
    for row in cap_rows if isinstance(cap_rows, list) else []:
        if not isinstance(row, dict) or row.get("id") not in cap_defs:
            return fail(f"unknown capability row: {row}")
        cid = str(row["id"])
        if cid in cap_status:
            return fail(f"duplicate capability status {cid}")
        cap_status[cid] = str(row.get("status", ""))
    missing_caps = sorted(cap_defs - set(cap_status))
    if missing_caps:
        return fail("coverage.capabilities must contain every capability registry row; missing: " + ", ".join(missing_caps))

    category_results: list[dict[str, Any]] = []
    overall_quality_num = 0.0
    overall_quality_den = 0.0
    overall_coverage_num = 0.0
    overall_coverage_den = 0.0
    overall_e6_weight = 0.0
    overall_scored_weight = 0.0

    for cid, cdef in categories.items():
        applicable_weight = 0.0
        scored_weight = 0.0
        score_num = 0.0
        e6_weight = 0.0

        for mdef in metric_defs:
            if mdef.get("category") != cid:
                continue
            mid = str(mdef["id"])
            metric = report_by_id.get(mid)
            if metric is None:
                # Missing registry rows are treated as not assessed/applicable only when minimum_public.
                if mdef.get("minimum_public"):
                    applicable_weight += float(mdef.get("weight", 0))
                continue
            if metric.get("applicable") is not True:
                if metric.get("status") != "not_applicable" or metric.get("score") is not None:
                    return fail(f"metric {mid} is not applicable and must use status not_applicable with null score")
                continue
            weight = float(mdef.get("weight", 0))
            applicable_weight += weight

            measurement_class = metric.get("measurement_class")
            capability_id = str(mdef.get("capability_id", ""))
            capability_state = cap_status.get(capability_id)
            if measurement_class in SCOREABLE_CLASSES and capability_state != "available":
                return fail(f"metric {mid} is {measurement_class} but capability {capability_id} is {capability_state}")
            if measurement_class == "not_assessed" and metric.get("status") != "not_assessed":
                return fail(f"applicable not_assessed metric {mid} must use status not_assessed")
            grade = str(metric.get("evidence_grade", "E8"))
            score = metric.get("score")

            if measurement_class not in SCOREABLE_CLASSES:
                if score is not None:
                    return fail(f"metric {mid} is {measurement_class} and must not have a score")
                continue
            if grade in {"E7", "E8"}:
                if score is not None:
                    return fail(f"metric {mid} uses {grade} and must not have a score")
                continue
            max_grade = str(mdef.get("max_evidence_grade", "E6"))
            if GRADE_RANK.get(grade, 99) > GRADE_RANK.get(max_grade, 6):
                if score is not None:
                    return fail(f"metric {mid} evidence {grade} is weaker than allowed {max_grade}")
                continue
            if score is None:
                continue
            if not isinstance(score, (int, float)) or not 0 <= float(score) <= 100:
                return fail(f"metric {mid} score must be 0-100 or null")
            status = str(metric.get("status", ""))
            anchors = registry.get("metric_score_scale", {})
            if status not in anchors:
                return fail(f"metric {mid} scored status {status!r} has no product anchor")
            expected_anchor = float(anchors[status])
            if float(score) != expected_anchor:
                return fail(f"metric {mid} score {score} must equal product anchor {expected_anchor:g} for status {status}")
            if mdef.get("score_mode") == "external_threshold" and not metric.get("threshold_source"):
                return fail(f"metric {mid} external-threshold score requires threshold_source")
            if not metric.get("source_or_method"):
                return fail(f"metric {mid} requires source_or_method")
            if not metric.get("does_not_prove"):
                return fail(f"metric {mid} requires does_not_prove")

            scored_weight += weight
            score_num += float(score) * weight
            if grade == "E6":
                e6_weight += weight

        coverage = (scored_weight / applicable_weight) if applicable_weight else 0.0
        cat_score = (score_num / scored_weight) if scored_weight else None
        cat_score_int = int(round(cat_score)) if cat_score is not None and coverage >= 0.50 else None
        cat_conf = confidence_label(coverage, e6_weight, scored_weight)

        category_results.append({
            "category": cid,
            "label": cdef.get("label_de", cid),
            "score": cat_score_int,
            "coverage_percent": int(round(coverage * 100)),
            "confidence": cat_conf,
        })

        category_weight = float(cdef.get("weight", 0))
        overall_coverage_num += category_weight * coverage
        overall_coverage_den += category_weight
        if cat_score is not None and coverage >= 0.50:
            overall_quality_num += cat_score * category_weight
            overall_quality_den += category_weight
            overall_e6_weight += category_weight * ((e6_weight / scored_weight) if scored_weight else 0.0)
            overall_scored_weight += category_weight

    overall_coverage = (overall_coverage_num / overall_coverage_den) if overall_coverage_den else 0.0
    assessed_quality = (overall_quality_num / overall_quality_den) if overall_quality_den else None
    coverage_percent = int(round(overall_coverage * 100))

    if overall_coverage >= 0.80 and assessed_quality is not None:
        display_status = "FULL_SCORE"
        label = "Pixelkiez Score"
        score_value: int | None = int(round(assessed_quality))
    elif overall_coverage >= 0.50 and assessed_quality is not None:
        display_status = "PARTIAL_SCORE"
        label = "Pixelkiez Teilscore"
        score_value = int(round(assessed_quality))
    else:
        display_status = "NO_SCORE"
        label = "Score nicht belastbar"
        score_value = None

    overall_confidence = confidence_label(
        overall_coverage,
        overall_e6_weight,
        overall_scored_weight,
    )
    blockers = [
        f for f in report.get("findings", [])
        if isinstance(f, dict) and f.get("severity") == "critical" and int(f.get("confidence", 0)) >= 4
    ]

    report["score_summary"] = {
        "policy_version": "2.0.0",
        "registry_version": str(registry.get("registry_version", "UNKNOWN")),
        "label": label,
        "score": score_value,
        "display_status": display_status,
        "coverage_percent": coverage_percent,
        "confidence": overall_confidence,
        "interpretation": interpretation(score_value),
        "blocker_present": bool(blockers),
        "category_scores": category_results,
        "does_not_prove": [
            "keine universelle Website-Qualität",
            "kein Ranking-, Umsatz- oder Conversion-Nachweis",
            "keine rechtliche oder WCAG-Konformität"
        ]
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"PASS: score={score_value if score_value is not None else 'N/A'} "
        f"coverage={coverage_percent}% status={display_status} confidence={overall_confidence}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
