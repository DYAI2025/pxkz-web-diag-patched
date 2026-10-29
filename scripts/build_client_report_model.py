#!/usr/bin/env python3
"""Build the concise Pixelkiez customer report model from a scored diagnosis report."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from client_story import clientize, confidence_de, plan_visual_story, select_client_levers
from customer_story_semantics import presentation_metadata, semantic_story_summary
from customer_status import customer_status
from evidence_method_labels import evidence_method, method_phrase
from legal_customer_projection import contested_identity_surface, contested_legal_surface, vouches_for_contested_legal_surface
from branch_priority import add_priority_arguments, load_priority_inputs, resolve_priority, selection_provenance

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


WHOLE_SITE_RX = re.compile(r"(?:auf\s+)?(?:der\s+)?gesamten?\s+(?:Website|Webseite|Seite|Auftritt)|\balle[nr]?\s+Seiten\b|\bsite-?wide\b|\büberall\b", re.I)
SAMPLE_SCOPED_METRICS = {"AI-06"}
UNASSESSED_CLASSES = {None, "", "not_assessed", "inferred_risk"}


def bound_strengths(report: dict[str, Any], limit: int) -> tuple[list[str], list[dict[str, Any]]]:
    """Customer strengths come only from positive findings whose linked metrics all read "Klar".

    One status scale: a metric the visuals label "Verbesserung sinnvoll" or worse cannot back a strength.
    Free-text executive_summary.top_strengths have no metric link and are recorded as not admitted.
    """
    metrics = {str(m.get("id")): m for m in report.get("metrics", []) if isinstance(m, dict)}
    contested = set(contested_legal_surface(report)) | set(contested_identity_surface(report))
    positives = sorted(
        [f for f in report.get("findings", []) if isinstance(f, dict) and f.get("severity") == "positive"],
        key=lambda f: (-int(f.get("confidence", 0)), str(f.get("id", ""))),
    )
    claims: list[dict[str, Any]] = []
    strengths: list[str] = []
    for f in positives:
        refs = [str(x) for x in f.get("metric_refs", []) if str(x).strip()]
        raw = str(f.get("client_observation") or f.get("title") or "")
        reasons: list[str] = []
        if not refs:
            reasons.append("NO_METRIC_REFS")
        for ref in refs:
            m = metrics.get(ref)
            if m is None or m.get("measurement_class") in UNASSESSED_CLASSES:
                reasons.append(f"METRIC_NOT_ASSESSED:{ref}")
            elif customer_status(m)["key"] != "CLEAR":
                reasons.append(f"METRIC_NOT_CLEAR:{ref}")
            if ref in contested:
                reasons.append(f"METRIC_CONTESTED:{ref}")
        if WHOLE_SITE_RX.search(raw):
            if refs and set(refs) <= SAMPLE_SCOPED_METRICS:
                raw = WHOLE_SITE_RX.sub("auf den geprüften Seiten", raw)
            else:
                reasons.append("WHOLE_SITE_WORDING")
        text = clientize(raw, limit)
        if vouches_for_contested_legal_surface(report, text):
            reasons.append("LEGAL_SURFACE_CONTESTED")
        if not text:
            reasons.append("EMPTY_TEXT")
        admitted = not reasons and text not in strengths and len(strengths) < 3
        if not reasons and not admitted:
            reasons.append("DUPLICATE_OR_LIMIT")
        claims.append({"text": text, "finding_ref": str(f.get("id")), "metric_refs": refs,
                       "evidence_refs": [str(e.get("id")) for e in f.get("evidence", []) if isinstance(e, dict) and e.get("id")],
                       "admitted": admitted, "reasons": reasons or ["BOUND_TO_CLEAR_METRICS"]})
        if admitted:
            strengths.append(text)
    executive = report.get("executive_summary") if isinstance(report.get("executive_summary"), dict) else {}
    known = {c["text"] for c in claims}
    for raw in executive.get("top_strengths", []) or []:
        text = clientize(raw, limit)
        if text and text not in known:
            claims.append({"text": text, "finding_ref": None, "metric_refs": [], "evidence_refs": [],
                           "admitted": False, "reasons": ["NO_FINDING_LINK"]})
            known.add(text)
    return strengths, claims


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
    # Values replayed from a fixture bundle are example data: no "real" label, no documented period.
    example = (str(enrichment.get("mode") or "").upper() in {"FIXTURE", "SYNTHETIC"}
               or any(evidence_method(x) == "SYNTHETIC" for x in metrics))
    sample = method_phrase("SYNTHETIC")
    # 1) current query-specific SERP result, only with explicit provider page if present
    pos = next((x for x in metrics if x.get("id") == "SERP_CURRENT_POSITION" and x.get("query")), None)
    if pos:
        page = next((x for x in metrics if x.get("id") == "SERP_CURRENT_PAGE" and x.get("query") == pos.get("query") and x.get("device") == pos.get("device") and x.get("location") == pos.get("location")), None)
        value = f"Position {int(pos.get('value'))}"
        if page and isinstance(page.get("value"), (int,float)):
            value += f" · Seite {int(page.get('value'))}"
        context = " · ".join(str(x) for x in (pos.get("query"), customer_location(pos.get("location")), customer_device(pos.get("device")), "Beispieldaten" if example else "") if x)
        out.append({"label":"Google-Sichtbarkeit", "value":value, "context":clientize(context, 100)})
    # 2) authorized real audience signal
    users = next((x for x in metrics if x.get("id") == "GA4_ACTIVE_USERS"), None)
    if users:
        value = f"{int(users.get('value')):,}".replace(",", ".") + " aktive Nutzer"
        dr = users.get("date_range") or {}
        context = f"{dr.get('start','')} bis {dr.get('end','')}" if isinstance(dr, dict) else "Dokumentierter Zeitraum"
        out.append({"label": "Nutzung" if example else "Reale Nutzung", "value": value, "context": sample if example else clientize(context, 100)})
    # 3) field performance, preferably phone
    field = next((x for x in metrics if x.get("id") == "CRUX_LCP_P75_MS" and str(x.get("device")).upper() == "PHONE"), None) or next((x for x in metrics if x.get("id") == "CRUX_LCP_P75_MS"), None)
    if field:
        sec = float(field.get("value"))/1000.0
        device = "Mobil" if str(field.get("device")).upper() == "PHONE" else (field.get("device") or "Feldwert")
        # LCP p75 says when the main content became visible for 75 % of visits, not a page load time.
        out.append({"label": "Ladeerfahrung" if example else "Reale Ladeerfahrung",
                    "value": f"Hauptinhalt sichtbar nach {sec:.1f} s (p75)".replace(".", ","),
                    "context": clientize(f"{device} · {'Beispieldaten' if example else 'dokumentierter Zeitraum'}", 100)})
    return out[:3]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("output")
    parser.add_argument("--visual-plan")
    add_priority_arguments(parser)
    parser.add_argument("--priority-decision-out", help="Internal-only selection provenance, not customer PDF")
    parser.add_argument("--claim-bindings-out", help="Internal-only strength-to-metric bindings, not customer PDF")
    try:
        args = parser.parse_args(argv[1:])
        report = load(Path(args.report))
        registry = load(REGISTRY_PATH)
        template = load(TEMPLATE_PATH)
        external_visual_plan = load(Path(args.visual_plan)) if args.visual_plan else None
        priority_context, priority_catalog = load_priority_inputs(
            args.priority_context, args.priority_catalog, args.priority_catalog_sha256
        )
        branch_weights, branch_roles, priority_decision = resolve_priority(
            report, priority_context, priority_catalog, allow_synthetic=args.priority_allow_synthetic
        )
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
    selected_levers = select_client_levers(
        report, max_levers=4, branch_weights=branch_weights, branch_roles=branch_roles
    )
    selected_ids = [str(f.get("id")) for f in selected_levers]
    if external_visual_plan is not None and external_visual_plan.get("top_levers", selected_ids) != selected_ids:
        return fail(
            "visual plan top_levers differ from customer lever selection: "
            f"{external_visual_plan.get('top_levers')} != {selected_ids}; build the plan with the same priority inputs"
        )
    if args.priority_decision_out:
        provenance = selection_provenance(report, selected_levers, branch_weights, branch_roles, priority_decision)
        Path(args.priority_decision_out).write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # Strengths are bound to positive findings whose metrics read "Klar"; see bound_strengths.
    strengths, claim_bindings = bound_strengths(report, budget("executive_strength", 110))

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
    # The audit's own roadmap entry (linked by evidence_basis) decides timing and priority of each lever, so the
    # roadmap, the next step and the closing actions follow one execution order instead of re-deriving P1/P2.
    source_roadmap = [x for x in report.get("roadmap", []) if isinstance(x, dict)]
    bucket_order = {"now": 0, "next_30_days": 1, "next_quarter": 2}
    scheduled = []
    for rank, f in enumerate(selected_levers):
        rec = f.get("recommendation") if isinstance(f.get("recommendation"), dict) else {}
        action = clientize(f.get("client_action") or rec.get("action"), budget("roadmap_action", 120))
        if not action:
            continue
        entry = next((x for x in source_roadmap if str(f.get("id")) in [str(y) for y in x.get("evidence_basis") or []]), {})
        horizon = entry.get("horizon") or rec.get("horizon")
        priority = entry.get("priority") if entry.get("priority") in {"P1", "P2", "P3"} else ("P1" if f.get("severity") in {"critical", "high"} else "P2")
        mandatory_critical = isinstance(f.get("customer_risk"), dict) and f["customer_risk"].get("priority") == "MANDATORY_CRITICAL"
        if f.get("severity") == "critical" or mandatory_critical:
            # A critical finding is never scheduled behind "Jetzt".
            bucket, priority = "now", "P1"
        elif horizon == "now":
            bucket = "now"
        elif horizon == "0_30_days":
            bucket = "next_30_days"
        else:
            bucket = "next_quarter"
        scheduled.append((bucket_order[bucket], rank, bucket, priority, action, f, rec))
    scheduled.sort(key=lambda x: (x[0], x[1]))
    for _, _, bucket, priority, action, f, rec in scheduled:
        if len(roadmap[bucket]) < 2:
            roadmap[bucket].append({"priority": priority, "action": action, "owner": clientize(rec.get("owner"), 55)})
    execution_ids = [str(x[5].get("id")) for x in scheduled]

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
    first_bucket = next((roadmap[k] for k in ("now", "next_30_days", "next_quarter") if roadmap[k]), [])
    if first_bucket:
        next_step = first_bucket[0]["action"]
    elif selected_levers:
        next_step = clientize(selected_levers[0].get("client_action") or selected_levers[0].get("recommendation", {}).get("action"), budget("recommendation_next_step", 160))
    rank_of = {fid: i for i, fid in enumerate(execution_ids)}
    closing_findings = sorted(finding_models[:4], key=lambda fm: rank_of.get(str(fm.get("id")), len(rank_of)))

    model = {
        "template_version": str(template.get("template_version", "5.0")),
        "brand": "Pixelkiez",
        "meta": {
            "customer": meta.get("customer_name", ""),
            "url": meta.get("audited_url", ""),
            "date": meta.get("audit_date", ""),
            "language": meta.get("language", "de"),
            # Example data stays recognizable on every page; real measurements never carry this key.
            **({"sample_data_notice": method_phrase("SYNTHETIC")}
               if any(evidence_method(m) == "SYNTHETIC" for m in report.get("metrics", []) if isinstance(m, dict)) else {}),
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
            "actions": [short_action(f.get("action")) for f in closing_findings],
            "cta": "Prioritäten bestätigen. Umsetzung starten.",
            "next_step": "Gemeinsam priorisieren wir die vier Hebel und starten mit dem ersten konkreten Umsetzungspaket.",
            "measurement_highlights": measurement_highlights(report),
        },
    }

    Path(args.output).write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.claim_bindings_out:
        bindings = {
            "schema_version": "1.0",
            "audited_url": str(meta.get("audited_url") or ""),
            "scored_report_sha256": hashlib.sha256(Path(args.report).read_bytes()).hexdigest(),
            "client_model_sha256": hashlib.sha256(Path(args.output).read_bytes()).hexdigest(),
            "rule": "strength admitted only from a positive finding whose metric_refs all read Klar and are uncontested",
            "claims": claim_bindings,
        }
        Path(args.claim_bindings_out).write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"PASS: client model with {len(categories)} categories, {len(finding_models)} levers, "
        f"{len(visualizations)} customer charts, visual_story={story_plan['visual_story_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
