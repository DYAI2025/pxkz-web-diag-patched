#!/usr/bin/env python3
"""Build the concise Pixelkiez customer report model from a scored diagnosis report."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from client_story import clientize, confidence_de, plan_visual_story, select_client_levers
from customer_story_semantics import presentation_metadata, semantic_story_summary
from branch_priority import choose_priority, validated_roles, load_json as load_priority_json

SKILL_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_DIR / "assets" / "measurement-registry.json"
TEMPLATE_PATH = SKILL_DIR / "templates" / "client-report-template.json"

ROUTE_DE = {
    "monitor": "Beobachten",
    "maintenance": "Gezielt pflegen",
    "targeted_modernization": "Gezielt modernisieren",
    "redesign": "Neu aufsetzen",
    "evidence_first": "Zuerst Messl\u00fccken schlie\u00dfen",
}


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def clip(text: object, limit: int) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    cut = value[: max(0, limit - 1)].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "\u2026"


def metric_status_summary(score: int | None, coverage: int) -> str:
    if score is None:
        return "Für diesen Bereich liegt kein belastbarer Bereichswert vor."
    if score >= 90:
        return "Im gepr\u00fcften Umfang sehr stark."
    if score >= 75:
        return "Stark, mit wenigen klaren L\u00fccken."
    if score >= 60:
        return "Solide Basis, gezielte Hebel sind sichtbar."
    if score >= 40:
        return "Mehrere relevante Verbesserungen sind sinnvoll."
    return "Grundlegende Schw\u00e4chen sollten zuerst behoben werden."


def scan_first_takeaway(priorities: list[str], strengths: list[str], fallback: object) -> str:
    if priorities:
        return clientize(f"Wichtigster Hebel: {priorities[0]}", 135)
    if strengths:
        return clientize(f"Stärkste Basis: {strengths[0]}", 135)
    return clientize(fallback, 135)


def scan_first_recommendation_reason(selected_levers: list[dict[str, Any]], fallback: object) -> str:
    if selected_levers:
        first = selected_levers[0]
        return clientize(first.get("client_observation") or first.get("title"), 135)
    return clientize(fallback, 135)


def short_action(value: object, limit: int = 125) -> str:
    """Preserve the complete approved action; never hide a verb by arbitrary clipping."""
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if "…" in text or "..." in text:
        raise ValueError("closing action contains a truncation marker; rewrite the upstream client_action")
    if len(text) > limit:
        raise ValueError(f"closing action exceeds {limit} characters; rewrite instead of truncating")
    if text[-1] not in ".!?":
        text += "."
    return text


def customer_location(value: object) -> str:
    text = " ".join(str(value or "").replace(",", ", ").split())
    return text.replace("Germany", "Deutschland")


def customer_device(value: object) -> str:
    raw = str(value or "").strip()
    return {"mobile": "Mobil", "phone": "Mobil", "desktop": "Desktop", "tablet": "Tablet"}.get(raw.casefold(), raw)


def measurement_highlights(report: dict[str, Any]) -> list[dict[str, str]]:
    enrichment = report.get("measurement_enrichment") if isinstance(report.get("measurement_enrichment"), dict) else {}
    metrics = [x for x in enrichment.get("metrics", []) if isinstance(x, dict) and x.get("status") in {"MEASURED", "OBSERVED"}]
    out: list[dict[str, str]] = []
    # 1) current query-specific SERP result, only with explicit provider page if present
    pos = next((x for x in metrics if x.get("id") == "SERP_CURRENT_POSITION" and x.get("query")), None)
    if pos:
        page = next((x for x in metrics if x.get("id") == "SERP_CURRENT_PAGE" and x.get("query") == pos.get("query") and x.get("device") == pos.get("device") and x.get("location") == pos.get("location")), None)
        value = f"Position {int(pos.get('value'))}"
        if page and isinstance(page.get("value"), (int,float)):
            value += f" · Seite {int(page.get('value'))}"
        context = " · ".join(str(x) for x in (pos.get("query"), customer_location(pos.get("location")), customer_device(pos.get("device"))) if x)
        out.append({"label":"Google-Sichtbarkeit", "value":value, "context":clientize(context, 100)})
    # 2) authorized real audience signal
    users = next((x for x in metrics if x.get("id") == "GA4_ACTIVE_USERS"), None)
    if users:
        value = f"{int(users.get('value')):,}".replace(",", ".") + " aktive Nutzer"
        dr = users.get("date_range") or {}
        context = f"{dr.get('start','')} bis {dr.get('end','')}" if isinstance(dr, dict) else "Dokumentierter Zeitraum"
        out.append({"label":"Reale Nutzung", "value":value, "context":clientize(context, 100)})
    # 3) field performance, preferably phone
    field = next((x for x in metrics if x.get("id") == "CRUX_LCP_P75_MS" and str(x.get("device")).upper() == "PHONE"), None) or next((x for x in metrics if x.get("id") == "CRUX_LCP_P75_MS"), None)
    if field:
        sec = float(field.get("value"))/1000.0
        device = "Mobil" if str(field.get("device")).upper() == "PHONE" else (field.get("device") or "Feldwert")
        out.append({"label":"Reale Ladeerfahrung", "value":f"Ladezeit p75 {sec:.1f} s".replace(".", ","), "context":clientize(f"{device} · dokumentierter Zeitraum", 100)})
    return out[:3]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("output")
    parser.add_argument("--visual-plan")
    parser.add_argument("--priority-context", help="Optional sourced sector/business-model context JSON")
    parser.add_argument("--priority-catalog", help="Optional approved industry weights catalog; no default estimates")
    parser.add_argument("--priority-catalog-sha256", help="Required exact SHA-256 for any external priority catalog")
    parser.add_argument("--priority-decision-out", help="Internal-only selection provenance, not customer PDF")
    try:
        args = parser.parse_args(argv[1:])
        report = load(Path(args.report))
        registry = load(REGISTRY_PATH)
        template = load(TEMPLATE_PATH)
        external_visual_plan = load(Path(args.visual_plan)) if args.visual_plan else None
        priority_context = load_priority_json(Path(args.priority_context)) if args.priority_context else None
        if args.priority_catalog:
            candidate = Path(args.priority_catalog)
            observed_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if not args.priority_catalog_sha256 or observed_sha != args.priority_catalog_sha256.lower():
                raise ValueError("external industry catalog requires matching --priority-catalog-sha256")
            priority_catalog = load_priority_json(candidate)
        elif args.priority_catalog_sha256:
            raise ValueError("priority catalog digest supplied without catalog")
        else:
            priority_catalog = None
        branch_weights, priority_decision = choose_priority(report, priority_context, priority_catalog)
        branch_roles = validated_roles(report, priority_context)
    except Exception as exc:
        return fail(str(exc))

    budgets = template.get("text_budgets", {})

    def budget(name: str, fallback: int) -> int:
        value = budgets.get(name, fallback)
        return int(value) if isinstance(value, (int, float)) and int(value) > 0 else fallback

    meta = report.get("meta", {})
    score = report.get("score_summary", {})
    executive = report.get("executive_summary", {})
    findings = [f for f in report.get("findings", []) if isinstance(f, dict)]
    positive = sorted(
        [f for f in findings if f.get("severity") == "positive"],
        key=lambda f: (-int(f.get("confidence", 0)), str(f.get("id", ""))),
    )
    selected_levers = select_client_levers(
        report, max_levers=4, branch_weights=branch_weights, branch_roles=branch_roles
    )
    if args.priority_decision_out:
        priority_decision["selected_lever_ids"] = [str(f.get("id")) for f in selected_levers]
        priority_decision["candidate_role_ids"] = sorted(branch_roles)
        priority_decision["customer_pdf_contains_priority_metadata"] = False
        priority_decision["canonical_core_score_unchanged"] = True
        Path(args.priority_decision_out).write_text(
            json.dumps(priority_decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    strengths = [clientize(x, budget("executive_strength", 110)) for x in executive.get("top_strengths", []) if str(x).strip()][:3]
    if len(strengths) < 3:
        for f in positive:
            candidate = clientize(f.get("client_observation") or f.get("title"), budget("executive_strength", 110))
            if candidate and candidate not in strengths:
                strengths.append(candidate)
            if len(strengths) == 3:
                break

    priorities: list[str] = []
    for f in selected_levers:
        candidate = clientize(f.get("title") or f.get("client_observation"), budget("executive_priority", 110))
        if candidate and candidate not in priorities:
            priorities.append(candidate)
        if len(priorities) == 3:
            break

    category_scores = score.get("category_scores", [])
    categories: list[dict[str, Any]] = []
    for item in category_scores:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category", ""))
        cat_findings = [f for f in selected_levers if f.get("category") == cat]
        summary = ""
        if cat_findings:
            summary = clientize(cat_findings[0].get("client_observation") or cat_findings[0].get("title"), budget("category_summary", 85))
        if not summary:
            summary = metric_status_summary(item.get("score"), int(item.get("coverage_percent", 0)))
        categories.append({
            "category": cat,
            "label": clientize(item.get("label", cat), 45),
            "score": item.get("score"),
            "coverage": int(item.get("coverage_percent", 0)),
            "summary": clientize(summary, budget("category_summary", 85)),
        })

    category_order = list(registry.get("categories", {}).keys())
    by_cat = {item["category"]: item for item in categories}
    categories = [by_cat[c] for c in category_order if c in by_cat]

    visualizations, story_plan = plan_visual_story(report, categories, selected_levers, registry, max_charts=3)
    story_plan["semantic_candidate_chart_count"] = len(visualizations)
    story_plan["visualization_plan_is_canonical"] = False
    story_plan["visualization_plan_source"] = None
    if external_visual_plan is not None:
        selected_external = [
            item for item in external_visual_plan.get("visuals", [])
            if isinstance(item, dict) and item.get("status") == "SELECTED"
        ]
        external_count = len(selected_external)
        story_plan.update({
            "real_chart_count": external_count,
            "target_real_charts": "4-7",
            "visual_story_status": "PASS" if 4 <= external_count <= 7 else "OUTSIDE_APPROVED_VISUAL_RANGE",
            "visualization_plan_is_canonical": True,
            "visualization_plan_source": Path(args.visual_plan).name,
            "semantic_candidate_chart_count": 0,
        })
        # The external visualization plan is canonical. Do not carry legacy scoring/method charts into the customer model.
        visualizations = []

    finding_models: list[dict[str, Any]] = []
    for f in selected_levers:
        evidence_refs: list[str] = []
        for ev in f.get("evidence", []):
            if isinstance(ev, dict) and ev.get("id"):
                evidence_refs.append(str(ev["id"]))
        semantic = presentation_metadata(report, f, registry)
        finding_models.append({
            "id": str(f.get("id", "")),
            "severity": str(f.get("severity", "medium")),
            "category": str(f.get("category", "")),
            "headline": clientize(f.get("title"), budget("finding_headline", 110)),
            "observation": clientize(f.get("client_observation") or f.get("observation"), budget("finding_observation", 130)),
            "impact": clientize(f.get("client_impact") or f.get("business_relevance", {}).get("text"), budget("finding_impact", 135)),
            "action": clientize(f.get("client_action") or f.get("recommendation", {}).get("action"), budget("finding_action", 125)),
            "evidence_refs": evidence_refs,
            "visual_asset": f.get("visual_asset"),
            **semantic,
        })

    roadmap = {"now": [], "next_30_days": [], "next_quarter": []}
    for f in selected_levers:
        rec = f.get("recommendation") if isinstance(f.get("recommendation"), dict) else {}
        action = clientize(f.get("client_action") or rec.get("action"), budget("roadmap_action", 120))
        if not action:
            continue
        horizon = rec.get("horizon")
        if horizon == "now":
            bucket = "now"
        elif horizon == "0_30_days":
            bucket = "next_30_days"
        else:
            bucket = "next_quarter"
        if len(roadmap[bucket]) < 2:
            roadmap[bucket].append({
                "priority": "P1" if f.get("severity") in {"critical", "high"} else "P2",
                "action": action,
                "owner": clientize(rec.get("owner"), 55),
            })

    display_status = str(score.get("display_status") or "NO_SCORE")
    numeric_score_visible = (
        display_status in {"FULL_SCORE", "PARTIAL_SCORE"}
        and isinstance(score.get("score"), (int, float))
        and not isinstance(score.get("score"), bool)
    )
    score_value = score.get("score") if numeric_score_visible else None
    score_label = (
        "Pixelkiez Score" if display_status == "FULL_SCORE" and numeric_score_visible
        else "Pixelkiez Bewertungsstand" if display_status == "PARTIAL_SCORE" and numeric_score_visible
        else ""
    )
    blocker_note = ""
    mandatory_risk = next((
        f for f in selected_levers
        if isinstance(f.get("customer_risk"), dict)
        and f["customer_risk"].get("priority") in {"MANDATORY_CRITICAL", "MANDATORY_HIGH"}
    ), None)
    if mandatory_risk is not None:
        blocker_note = clientize(mandatory_risk.get("customer_risk", {}).get("warning_label"), 80)
    elif numeric_score_visible and score.get("blocker_present"):
        blocker_note = "Ein kritischer Website-Befund bleibt trotz Gesamtwert sichtbar."
    # The cover takeaway must be a customer-specific website finding, not a generic score band.
    cover_verdict = scan_first_recommendation_reason(selected_levers, executive.get("decision") or score.get("interpretation"))

    next_step = "Die wichtigsten Maßnahmen zuerst umsetzen."
    if selected_levers:
        next_step = clientize(selected_levers[0].get("client_action") or selected_levers[0].get("recommendation", {}).get("action"), budget("recommendation_next_step", 160))

    model = {
        "template_version": str(template.get("template_version", "5.0")),
        "brand": "Pixelkiez",
        "meta": {
            "customer": meta.get("customer_name", ""),
            "url": meta.get("audited_url", ""),
            "date": meta.get("audit_date", ""),
            "language": meta.get("language", "de"),
        },
        "cover": {
            "eyebrow": "01 · WEBSITE-ANALYSE",
            "title": "Was Ihre Website heute gut macht - und was sie bremst.",
            "customer": meta.get("customer_name", ""),
            "url": meta.get("audited_url", ""),
            "date": meta.get("audit_date", ""),
            "score_label": score_label,
            "score": score_value,
            "verdict": cover_verdict,
            "blocker_note": blocker_note,
        },
        "executive": {
            "takeaway": scan_first_takeaway(priorities, strengths, executive.get("decision") or score.get("interpretation")),
            "strengths": strengths,
            "priorities": priorities,
            "recommended_route": ROUTE_DE.get(executive.get("recommended_route"), clientize(executive.get("recommended_route", ""), 60)),
        },
        "categories": [
            {k: v for k, v in item.items() if k != "coverage"}
            for item in categories
        ],
        "client_story": story_plan,
        "semantic_story": semantic_story_summary(finding_models),
        "visualizations": visualizations,
        "findings": finding_models,
        "roadmap": roadmap,
        "recommendation": {
            "route": ROUTE_DE.get(executive.get("recommended_route"), clientize(executive.get("recommended_route", ""), 60)),
            "reason": scan_first_recommendation_reason(selected_levers, executive.get("decision")),
            "next_step": next_step,
        },
        "closing": {
            "eyebrow": "NÄCHSTER SCHRITT",
            "title": "Aus Analyse wird Umsetzung.",
            "summary": "Die wichtigsten Stellschrauben sind klar. Jetzt geht es darum, sie in der richtigen Reihenfolge umzusetzen und die geschäftliche Wirkung zu verbessern.",
            "actions": [short_action(f.get("action")) for f in finding_models[:4]],
            "cta": "Prioritäten bestätigen. Umsetzung starten.",
            "next_step": "Gemeinsam priorisieren wir die vier Hebel und starten mit dem ersten konkreten Umsetzungspaket.",
            "measurement_highlights": measurement_highlights(report),
        },
    }

    Path(args.output).write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"PASS: client model with {len(categories)} categories, {len(finding_models)} levers, "
        f"{len(visualizations)} customer charts, visual_story={story_plan['visual_story_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
