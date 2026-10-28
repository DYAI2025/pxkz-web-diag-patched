#!/usr/bin/env python3
"""Build a deterministic, evidence-bound Pixelkiez visualization plan."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime

from customer_status import STATUS_META, customer_status
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from branch_priority import add_priority_arguments, load_priority_inputs, resolve_priority  # noqa: E402
from client_story import clientize, select_client_levers  # noqa: E402
from legal_customer_projection import contested_identity_surface, contested_legal_surface  # noqa: E402
from strategic_relevance import eligible_findings  # noqa: E402
from visualization_policy import apply_customer_visual_budget, CUSTOMER_MIN_VISUALS  # noqa: E402

SEVERITY_WEIGHT = {"critical": 100, "high": 80, "medium": 60, "low": 40, "positive": 20}
RATIO_RE = re.compile(r"(\d+)\s*(?:of|von|/)\s*(\d+)", re.I)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def customer_location(value: object) -> str:
    text = " ".join(str(value or "").replace(",", ", ").split())
    return text.replace("Germany", "Deutschland")


def customer_device(value: object) -> str:
    raw = str(value or "").strip()
    return {"mobile": "Mobil", "phone": "Mobil", "desktop": "Desktop", "tablet": "Tablet"}.get(raw.casefold(), raw)


def customer_date(value: object) -> str:
    raw = str(value or "").strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%d.%m.%Y")
    except Exception:
        return raw[:10]


def plain_text(value: Any, max_length: int, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"{field} must not be blank")
    if len(text) > max_length:
        raise ValueError(f"{field} exceeds {max_length} characters; rewrite instead of truncating")
    if "…" in text or "..." in text:
        raise ValueError(f"{field} contains truncation marker")
    return text


def evidence_class(metrics: list[dict[str, Any]]) -> str:
    classes = {str(x.get("measurement_class")) for x in metrics}
    if not classes:
        return "DERIVED"
    if classes <= {"measured", "observed"}:
        return "DIRECT"
    if "inferred_risk" in classes:
        return "MIXED_WITH_INFERENCE"
    if classes <= {"not_assessed"}:
        return "NOT_ASSESSED"
    return "MIXED"


def metric_label(defs: dict[str, dict[str, Any]], metric: dict[str, Any]) -> str:
    return clientize(defs.get(str(metric.get("id")), {}).get("label_de") or metric.get("id"), 44)


def visual(vid: int, template: str, title: str, subtitle: str, metric_refs: list[str], finding_refs: list[str], eclass: str, population: str, method: str, boundary: str, data: Any, engine: str = "VEGA_LITE") -> dict[str, Any]:
    return {
        "id": f"VIZ-{vid:03d}",
        "template_id": template,
        "engine": engine,
        "status": "SELECTED",
        "title": plain_text(title, 120, "visual.title"),
        "subtitle": plain_text(subtitle, 160, "visual.subtitle") if str(subtitle or "").strip() else "",
        "metric_refs": metric_refs,
        "finding_refs": finding_refs,
        "evidence_class": eclass,
        "population": population,
        "method": method,
        "does_not_prove": boundary,
        "data": data,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report")
    ap.add_argument("output")
    add_priority_arguments(ap)
    args = ap.parse_args()
    report_path, output = Path(args.report).resolve(), Path(args.output).resolve()
    root = Path(__file__).resolve().parents[1]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        registry = json.loads((root / "assets/measurement-registry.json").read_text(encoding="utf-8"))
        brand_path = root / "assets/brand-tokens.json"
        defs = {str(x.get("id")): x for x in registry.get("metrics", []) if isinstance(x, dict)}
        metrics = [x for x in report.get("metrics", []) if isinstance(x, dict)]
        metric_by_id = {str(x.get("id")): x for x in metrics}
        findings = eligible_findings(report)
        priority_context, priority_catalog = load_priority_inputs(
            args.priority_context, args.priority_catalog, args.priority_catalog_sha256
        )
        branch_weights, branch_roles, _ = resolve_priority(
            report, priority_context, priority_catalog, allow_synthetic=args.priority_allow_synthetic
        )
        levers = select_client_levers(report, 4, branch_weights=branch_weights, branch_roles=branch_roles)
        if len(levers) != 4:
            raise ValueError("exactly four strategically relevant customer levers are required")
        visuals: list[dict[str, Any]] = []
        excluded: list[dict[str, str]] = []
        vid = 1
        score = report.get("score_summary", {}) if isinstance(report.get("score_summary"), dict) else {}
        overall = score.get("score")
        excluded.append({"template_id": "V01_OVERALL_SCORE", "reason": "COVER_OR_OVERVIEW_ONLY_NO_DUPLICATE_CHART_PAGE"})

        cats = []
        if score.get("display_status") == "FULL_SCORE":
            for c in score.get("category_scores", []) if isinstance(score.get("category_scores"), list) else []:
                if isinstance(c.get("score"), (int, float)) and not isinstance(c.get("score"), bool):
                    cats.append({"label": clientize(c.get("label") or c.get("category"), 36), "value": float(c["score"])})
        if len(cats) >= 2:
            visuals.append(visual(vid, "V02_CATEGORY_BARS", "Stärken und Schwächen nach Bereich", "Wie die wichtigsten Bereiche der Website heute abschneiden", [f"CATEGORY:{c.get('category')}" for c in score.get("category_scores", [])], [], "DERIVED", f"{len(cats)} bewertete Kategorien", "Pixelkiez Bewertungsmodell", "Bereichswerte sind keine externen Benchmarks und beweisen keine Geschäftswirkung.", cats)); vid += 1
        else:
            excluded.append({"template_id": "V02_CATEGORY_BARS", "reason": "NO_CUSTOMER_FULL_SCORE_OR_TOO_FEW_CATEGORIES"})

        lever_rows = []
        lever_refs = []
        lever_metric_refs = []
        for rank, f in enumerate(levers, 1):
            lever_rows.append({"label": plain_text(clientize(f.get("client_observation") or f.get("title"), 130), 130, f"lever {rank} label"), "priority": rank})
            lever_refs.append(str(f.get("id")))
            lever_metric_refs.extend(str(x) for x in f.get("metric_refs", []))
        visuals.append(visual(vid, "V03_TOP_LEVERS", "Die vier wichtigsten Hebel", "Priorisiert nach geschäftlicher Bedeutung und Dringlichkeit", list(dict.fromkeys(lever_metric_refs)), lever_refs, "DERIVED_FROM_FINDINGS", "Vier priorisierte Website-Hebel", "Interne Priorisierung", "Die Rangfolge ist ordinal. Sie enthält keine gemessene Größe, Umsatz- oder Aufwandsschätzung.", lever_rows)); vid += 1

        # Prefer a directly measured threshold visualization already attached to the audit.
        threshold_source = None
        for item in report.get("visualizations", []) if isinstance(report.get("visualizations"), list) else []:
            if not isinstance(item, dict) or item.get("template_id") != "V02":
                continue
            refs = [str(x) for x in item.get("metric_refs", [])]
            linked = [metric_by_id[x] for x in refs if x in metric_by_id]
            if not linked or not all(x.get("measurement_class") in {"measured", "observed"} for x in linked):
                continue
            series = item.get("data", {}).get("series", []) if isinstance(item.get("data"), dict) else []
            bands = item.get("data", {}).get("bands", []) if isinstance(item.get("data"), dict) else []
            if not series:
                continue
            current = float(series[-1].get("value"))
            good = next((float(x.get("boundary")) for x in bands if x.get("status") == "good"), None)
            warn = next((float(x.get("boundary")) for x in bands if x.get("status") == "warn"), None)
            if good is None or warn is None:
                continue
            ev = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
            finding_ref = str(item.get("finding_ref") or "").strip()
            finding = next((f for f in findings if str(f.get("id")) == finding_ref), None)
            customer_title = clientize(
                (finding or {}).get("client_observation")
                or "Der wichtigste sichtbare Inhalt lädt auf Mobilgeräten langsamer als empfohlen.",
                120,
            )
            customer_subtitle = "Mobile Ladezeit im Vergleich zum Zielwert"
            customer_metric_label = "Mobile Ladezeit"
            threshold_source = visual(
                vid,
                "V07_PERFORMANCE_THRESHOLD",
                customer_title,
                customer_subtitle,
                refs,
                [finding_ref] if finding_ref else [],
                evidence_class(linked),
                str(ev.get("population") or f"{len(series)} Messpunkte"),
                f"{ev.get('tool', 'Audit measurement')} {ev.get('version', '')}".strip(),
                str(item.get("does_not_prove") or linked[0].get("does_not_prove") or "Keine Geschäftswirkung belegt."),
                [{"label": customer_metric_label, "value": current, "good": good, "warn": warn}],
            )
            break
        if threshold_source:
            visuals.append(threshold_source); vid += 1
        else:
            excluded.append({"template_id": "V07_PERFORMANCE_THRESHOLD", "reason": "NO_DIRECT_VALUE_WITH_SUPPORTED_THRESHOLD"})

        sev = Counter(str(f.get("severity")) for f in findings)
        severity_de = {"critical": "kritisch", "high": "hoch", "medium": "mittel", "low": "niedrig"}
        sev_rows = [{"group": "Befunde", "severity": severity_de[key], "count": sev.get(key, 0)} for key in ("critical", "high", "medium", "low") if sev.get(key, 0)]
        if sev_rows:
            all_refs = list(dict.fromkeys(str(x) for f in findings for x in f.get("metric_refs", [])))
            visuals.append(visual(vid, "V11_SEVERITY_DISTRIBUTION", "Befunde nach Dringlichkeit", "Verteilung der priorisierbaren Befunde", all_refs, [str(f.get("id")) for f in findings], "CLASSIFIED_FINDINGS", f"{len(findings)} Verbesserungsbefunde", "Finding severity inventory", "Die Anzahl der Befunde misst weder Aufwand noch wirtschaftliche Wirkung.", sev_rows)); vid += 1

        excluded.append({"template_id": "V12_AUDIT_COVERAGE", "reason": "INTERNAL_ONLY_NOT_CUSTOMER_VISIBLE"})

        contested = contested_legal_surface(report)
        # A metric that a customer-visible problem finding cites (or an identity metric next to a projected
        # provider-identity risk) must not read as clear on the same PDF.
        capped = {str(x) for f in findings for x in f.get("metric_refs", [])} | contested_identity_surface(report)

        def category_matrix(category: str, template: str, title: str, label_name: str, *, four_state: bool = False) -> None:
            nonlocal vid
            rows = []
            refs = []
            for m in metrics:
                mid = str(m.get("id"))
                if defs.get(mid, {}).get("category") != category:
                    continue
                if m.get("measurement_class") == "not_assessed":
                    continue
                if four_state:
                    # A projected legal customer risk outranks the presence-only core status on the customer label.
                    state = {"key": "ACTION", **STATUS_META["ACTION"]} if mid in contested else customer_status(m)
                    if state["key"] == "CLEAR" and mid in capped:
                        state = {"key": "IMPROVE", **STATUS_META["IMPROVE"]}
                    rows.append({label_name: metric_label(defs, m), "status": state["label"], "symbol": state["symbol"], "tone": state["tone"], "value": state["value"]})
                    refs.append(mid)
                    continue
                sc = m.get("score")
                if not isinstance(sc, (int, float)) or isinstance(sc, bool):
                    continue
                value = max(0.0, min(1.0, float(sc) / 100.0))
                if mid in capped:
                    value = min(value, .74)
                status = "klar" if value >= .75 else "teilweise" if value >= .5 else "offen"
                rows.append({label_name: metric_label(defs, m), "status": status, "value": value})
                refs.append(mid)
            if len(rows) >= 3:
                subtitle = "Wo Handlungsbedarf besteht und was bereits trägt" if four_state else "Wie klar dieser Bereich heute aufgestellt ist"
                limitation = "Handlungsbedarf ist ein technischer/inhaltlicher Befund und keine juristische Feststellung." if four_state else "Die Matrix ist kein Marktbenchmark und keine Erfolgsprognose."
                visuals.append(visual(vid, template, title, subtitle, refs, [], evidence_class([metric_by_id[x] for x in refs]), f"{len(rows)} Aspekte in diesem Bereich", "Pixelkiez four-state customer status projection" if four_state else "Pixelkiez metric-status projection", limitation, rows[:8])); vid += 1
            else:
                excluded.append({"template_id": template, "reason": "TOO_FEW_ELIGIBLE_CATEGORY_METRICS"})
        category_matrix("ai_readiness", "V08_AI_ANSWERABILITY", "Wie klar die Website für KI-Systeme ist", "question")
        category_matrix("trust_privacy_content", "V10_TRUST_MATRIX", "Vertrauen und Konsistenz", "signal", four_state=True)

        ranking_added = False
        enrichment = report.get("measurement_enrichment") if isinstance(report.get("measurement_enrichment"), dict) else {}
        enrichment_metrics = [x for x in enrichment.get("metrics", []) if isinstance(x, dict)]
        serp_positions = [x for x in enrichment_metrics if x.get("id") == "SERP_CURRENT_POSITION" and x.get("status") in {"MEASURED", "OBSERVED"} and x.get("query") and isinstance(x.get("value"), (int, float))]
        if serp_positions:
            page_by_key = {(x.get("query"), x.get("device"), x.get("location")): x.get("value") for x in enrichment_metrics if x.get("id") == "SERP_CURRENT_PAGE" and x.get("status") in {"MEASURED", "OBSERVED"}}
            rankings = [{"query": x.get("query"), "position": int(x.get("value")), "page": page_by_key.get((x.get("query"), x.get("device"), x.get("location"))), "device": x.get("device"), "location": x.get("location"), "observed_at": x.get("observed_at")} for x in serp_positions]
            first = serp_positions[0]
            context = " · ".join(str(x) for x in [customer_location(first.get("location")), customer_device(first.get("device")), customer_date(first.get("observed_at"))] if x)
            visuals.append(visual(vid, "V05_RANKING_POSITION", "Google-Positionen nach Suchanfrage", context or "Aktueller Suchstand", [], [], "MEASURED_SERP", f"{len(rankings)} dokumentierte Suchanfragen", str(first.get("source_provider") or "SERP provider"), "Rankings gelten nur für Query, Ort, Gerät, Zeitpunkt und Messmethode und sind keine dauerhafte Position.", rankings)); vid += 1
            ranking_added = True

        benchmark = report.get("benchmark_data")
        if isinstance(benchmark, dict) and all(benchmark.get(k) for k in ("measured_at", "method", "location", "entities")):
            entities = benchmark.get("entities")
            if isinstance(entities, list) and len(entities) >= 2 and all(isinstance(x, dict) and isinstance(x.get("value"), (int, float)) for x in entities):
                visuals.append(visual(vid, "V04_FINDABILITY_BENCHMARK", "Auffindbarkeit im dokumentierten Vergleich", f"Stand {benchmark['measured_at']} · {benchmark['location']}", [str(x) for x in benchmark.get("metric_refs", [])], [], "MEASURED_BENCHMARK", f"{len(entities)} dokumentierte Vergleichsobjekte", str(benchmark["method"]), "Der Vergleich gilt nur für dokumentierte Queries, Ort, Gerät, Zeitpunkt und Stichprobe.", entities)); vid += 1
            rankings = benchmark.get("rankings")
            if not ranking_added and isinstance(rankings, list) and rankings and all(isinstance(x, dict) and x.get("query") and isinstance(x.get("position"), int) for x in rankings):
                visuals.append(visual(vid, "V05_RANKING_POSITION", "Google-Positionen nach Suchanfrage", f"Stand {benchmark['measured_at']} · {benchmark['location']}", [str(x) for x in benchmark.get("metric_refs", [])], [], "MEASURED_SERP", f"{len(rankings)} dokumentierte Suchanfragen", str(benchmark["method"]), "Rankings gelten nur für Query, Ort, Gerät, Zeitpunkt und Messmethode und sind keine dauerhafte Position.", rankings)); vid += 1
        else:
            excluded.append({"template_id": "V04_FINDABILITY_BENCHMARK", "reason": "BENCHMARK_CONTEXT_MISSING"})
            if not ranking_added:
                excluded.append({"template_id": "V05_RANKING_POSITION", "reason": "SERP_QUERY_CONTEXT_MISSING"})

        # Non-selected approved advanced templates remain explicit rather than silently omitted.
        selected_ids = {x["template_id"] for x in visuals}
        for tid, reason in [
            ("V06_QUERY_COVERAGE", "NO_QUERY_LEVEL_MATRIX"),
            ("V09_AGENT_READINESS", "NO_AGENT_TASK_MATRIX"),
            ("V13_IMPACT_EFFORT", "NO_EVIDENCE_BOUND_EFFORT_VALUES"),
            ("V14_REPEAT_AUDIT", "NO_PREVIOUS_COMPARABLE_AUDIT"),
            ("D01_PROCESS_FLOW", "NO_STRUCTURAL_FLOW_REQUIRED_FOR_TOP_STORY"),
        ]:
            if tid not in selected_ids and not any(x["template_id"] == tid for x in excluded):
                excluded.append({"template_id": tid, "reason": reason})

        # Customer-visible strings pass the same plain-language firewall as the client model.
        for item in visuals:
            for field, limit in (("title", 130), ("subtitle", 150)):
                if item.get(field) is not None:
                    item[field] = clientize(item.get(field), limit)
        visuals, budget_overflow = apply_customer_visual_budget(visuals)
        for item in budget_overflow:
            excluded.append({
                "template_id": str(item.get("template_id")),
                "reason": "CUSTOMER_PAGE_BUDGET_MAX_7",
            })
        if len(visuals) < CUSTOMER_MIN_VISUALS:
            raise ValueError(f"customer visualization plan requires at least {CUSTOMER_MIN_VISUALS} selected visuals")

        payload = {
            "schema_version": "1.0",
            "source_report_sha256": sha(report_path),
            "brand_token_sha256": sha(brand_path),
            "top_levers": [str(x.get("id")) for x in levers],
            "visuals": visuals,
            "excluded_candidates": excluded,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: visualization plan selected={len(visuals)} excluded={len(excluded)} top_levers=4")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
