#!/usr/bin/env python3
"""Render the complete internal Pixelkiez analysis report as deterministic Markdown."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("analysis_json")
    ap.add_argument("output")
    args = ap.parse_args()
    src, out = Path(args.analysis_json).resolve(), Path(args.output).resolve()
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        customer = meta.get("customer_name") or meta.get("company") or "Unbekanntes Unternehmen"
        website = meta.get("website") or meta.get("url") or "-"
        lines = [
            f"# Vollständige Website-Analyse: {customer}",
            "",
            f"- Website: {website}",
            f"- Audit-ID: {meta.get('audit_id', '-')}",
            f"- Erhebungsdatum: {meta.get('audit_date', meta.get('generated_at', '-'))}",
            f"- Quellbericht SHA-256: `{data['source_report_sha256']}`",
            "",
            "## Executive Summary",
            "",
            text(data.get("executive_summary", {}).get("decision") or data.get("score_summary", {}).get("interpretation")),
            "",
            "## Score und Kategorien",
            "",
            f"- Gesamtscore: {text(data.get('score_summary', {}).get('score'))}",
            f"- Darstellungsstatus: {text(data.get('score_summary', {}).get('display_status'))}",
            f"- Abdeckung: {text(data.get('score_summary', {}).get('coverage_percent'))} %",
            "",
            "| Kategorie | Score | Abdeckung | Status | Metriken |",
            "|---|---:|---:|---|---:|",
        ]
        for c in data.get("categories", []):
            lines.append(f"| {text(c.get('label'))} | {text(c.get('score'))} | {text(c.get('coverage'))} | {text(c.get('status'))} | {text(c.get('metric_count'))} |")
        lines += ["", "## Vollständige Metriken", ""]
        for metric in data.get("metrics", []):
            lines += [
                f'<a id="metric-{metric["id"].lower()}"></a>',
                f"### `{metric['id']}` - {metric['label']}",
                "",
                f"- Kategorie: {metric['category']}",
                f"- Anwendbar: {str(metric['applicable']).lower()}",
                f"- Messklasse: {metric['measurement_class']}",
                f"- Evidenzklasse: {metric['evidence_grade']}",
                f"- Status: {text(metric['status'])}",
                f"- Wert: {text(metric['value'])}{(' ' + str(metric['unit'])) if metric.get('unit') else ''}",
                f"- Score: {text(metric['score'])}",
                f"- Score zugelassen: {str(bool(metric.get('score_admitted'))).lower()}",
                f"- Metrikgewicht: {text(metric.get('metric_weight'))}",
                f"- Kategoriegewicht: {text(metric.get('category_weight'))}",
                f"- Gewichteter Beitrag: {text(metric.get('weighted_contribution'))}",
                f"- Konfidenz: {text(metric['confidence'])}",
                f"- Methode/Quelle: {metric['source_or_method']}",
                f"- Schwellenherkunft: {text(metric['threshold_source'])}",
                f"- Evidenzreferenzen: {', '.join(metric['evidence_refs']) if metric['evidence_refs'] else '-'}",
                f"- Technische Einordnung: {metric['interpretation']}",
                f"- Unternehmerische Frage: {metric['business_question']}",
                f"- Wirkungskanal: {metric['business_effect_channel']}",
                f"- Business-Bedeutung: {metric['business_interpretation']}",
                f"- Visual Decision: {text(metric['visual_decision'])}",
                f"- Beweist nicht: {metric['does_not_prove']}",
                f"- Maßnahmenstatus: {metric['action_state']}",
                f"- Verknüpfte Empfehlungen: {', '.join(metric['recommendation_refs']) if metric['recommendation_refs'] else 'NO_ACTION'}",
                "",
            ]
        lines += ["## Befunde", ""]
        for f in data.get("findings", []):
            rec = f.get("recommendation", {}) if isinstance(f.get("recommendation"), dict) else {}
            lines += [
                f"### {text(f.get('id'))}: {text(f.get('title'))}",
                "",
                f"- Kategorie: {text(f.get('category'))}",
                f"- Schwere: {text(f.get('severity'))}",
                f"- Beobachtung: {text(f.get('observation'))}",
                f"- Kundenwirkung: {text(f.get('client_impact') or f.get('business_relevance'))}",
                f"- Maßnahme: {text(rec.get('action') or f.get('client_action'))}",
                f"- Verantwortlich: {text(rec.get('owner'))}",
                f"- Horizont: {text(rec.get('horizon'))}",
                f"- Abnahmetest: {text(rec.get('acceptance_test'))}",
                "",
            ]
        lines += ["## Priorisierte Maßnahmen", ""]
        for rec in data.get("recommendations", []):
            lines += [
                f"### {rec['id']}",
                "",
                f"- Befund: {rec['finding_id']}",
                f"- Schwere: {text(rec.get('severity'))}",
                f"- Maßnahme: {rec['action']}",
                f"- Verantwortlich: {rec['owner']}",
                f"- Horizont: {rec['horizon']}",
                f"- Abnahmetest: {rec['acceptance_test']}",
                "",
            ]
        enrichment = data.get("measurement_enrichment") if isinstance(data.get("measurement_enrichment"), dict) else None
        lines += ["## Messdaten-Enrichment", ""]
        if enrichment:
            lines += [f"- Modus: {text(enrichment.get('mode'))}", f"- Erzeugt: {text(enrichment.get('generated_at'))}", "", "### Datenquellen", ""]
            for source in enrichment.get("sources", []):
                if isinstance(source, dict):
                    lines.append(f"- {text(source.get('provider'))}: {text(source.get('status'))} - {text(source.get('note'))}")
            lines += ["", "### Enrichment-Metriken", ""]
            for metric in enrichment.get("metrics", []):
                if not isinstance(metric, dict): continue
                ctx = []
                for key in ("query","location","device","date_range"):
                    if metric.get(key): ctx.append(f"{key}={metric.get(key)}")
                lines += [f"- `{text(metric.get('id'))}`: {text(metric.get('value'))} {text(metric.get('unit'))} | {text(metric.get('source_provider'))} | {', '.join(ctx) if ctx else '-'} | Grenze: {text(metric.get('claim_boundary'))}"]
        else:
            lines.append("- Keine externe Messdaten-Anreicherung beigefügt.")
        lines += [""]
        vc=data.get("vibecheck03") if isinstance(data.get("vibecheck03"),dict) else None
        lines += ["## Vibe-Check #03 (nicht scorewirksam)", ""]
        if vc:
            lines += [f"- Run: {text(vc.get('run_id'))}", f"- URL: {text(vc.get('page_url'))}", ""]
            lines += [f"- Quelle: {text(vc.get('source_authority'))} | Stichprobe vollständig: {text(vc.get('sample_complete'))} | Score-Wirkung: {text(vc.get('score_effect'))}", ""]
            for row in vc.get('metrics',[]):
                if isinstance(row,dict): lines.append(f"- `{text(row.get('metric_id'))}`: {text(row.get('status'))} / {text(row.get('value'))} / {text(row.get('reason'))} / {text(row.get('evidence_ref'))} | {text(row.get('method'))} {text(row.get('collector_version'))} | {text(row.get('observed_at'))} | Review: {text(row.get('manual_review_required'))} | Szenario: {text(row.get('scenario'))}")
            if vc.get('metrics'):
                lines += ["", f"- Grenze: {text(vc['metrics'][0].get('claim_boundary'))}"]
            adm=data.get("vibecheck03_admission") if isinstance(data.get("vibecheck03_admission"),dict) else None
            if adm:
                lines += ["", "### Kundenzulassung VC03 (Route VC03_DIAGNOSTIC)", "", f"- Regelversion: {text(adm.get('rules_version'))} | Bindungsfehler: {text(', '.join(adm.get('binding_errors') or []) or 'keine')}"]
                for rule in adm.get("rules", []):
                    detail = "; ".join(f"{text(x.get('finding_id'))}: {text(', '.join(x.get('reasons') or []) or 'zulässig')}{' (Kundenhebel)' if x.get('selected_in_default_customer_levers') else ' (nicht unter den vier Hebeln)'}" for x in rule.get("findings", []))
                    missing = ", ".join(rule.get("not_assessed_metrics") or [])
                    lines.append(f"- `{text(rule.get('rule_id'))}`: {text(rule.get('status'))}" + (f" | {detail}" if detail else "") + (f" | nicht bewertet: {missing}" if missing else ""))
                lines.append("- Nicht bewertete Signale gelten nicht als Schwäche.")
        else: lines.append("- Keine Vibe-Check-03-Diagnostik angefügt.")
        lines.append("")
        lines += ["## Quellen und Methoden", ""]
        for source in data.get("sources", []):
            lines += [
                f"### {text(source.get('id'))}: {text(source.get('title'))}",
                "",
                f"- Typ: {text(source.get('type'))}",
                f"- Ort: {text(source.get('location'))}",
                f"- Zweck: {text(source.get('purpose'))}",
                "",
            ]
        lines += ["## Abdeckung, Grenzen und offene Evidenz", "", "### Abdeckung", "", "```json", json.dumps(data.get("coverage", {}), ensure_ascii=False, indent=2, sort_keys=True), "```", "", "### Grenzen", ""]
        for item in data.get("limitations", []): lines.append(f"- {text(item)}")
        lines += ["", "### MISSING", ""]
        for item in data.get("missing", []): lines.append(f"- {text(item)}")
        lines += ["", "### SOURCE_NEEDED", ""]
        for item in data.get("source_needed", []): lines.append(f"- {text(item)}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"PASS: rendered internal markdown metrics={len(data.get('metrics', []))}")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
