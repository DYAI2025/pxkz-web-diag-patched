#!/usr/bin/env python3
"""Create a fail-closed semantic customer-QA manifest bound to PDF, client model and audit.

Creation never certifies semantic quality. A vision-capable agent or human must inspect the
actual rendered PDF against the client model and canonical scored audit before setting PASS.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from pypdf import PdfReader

OVERALL_CHECKS = [
    "customer_specificity",
    "plain_language_comprehension",
    "scan_first_story",
    "evidence_fidelity",
    "priority_quality",
    "quantitative_content_visualized",
    "cross_page_coherence",
    "actionability",
    "no_generic_agency_copy",
    "no_unsupported_business_claims",
    "cover_message_complete",
    "score_projection_correct",
    "lever_business_impact_complete",
    "privacy_claim_scope_correct",
    "no_synthetic_metric_visuals",
]
PAGE_CHECKS = [
    "customer_specific",
    "main_message_clear",
    "scan_in_seconds",
    "plain_language",
    "evidence_faithful",
    "visual_semantic_fit",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page_role(text: str, page_number: int) -> str:
    if page_number == 1:
        return "cover"
    u=" ".join(text.upper().split())
    for marker, role in [
        ("AUF EINEN BLICK","executive"),("KATEGORIE-SCORES","categories"),
        ("WEBSITE-BEFUND","decision_visual"),
        ("AUS ANALYSE WIRD UMSETZUNG","closing"),
        ("VIER HEBEL","findings"),("PRIORISIERTE BEFUNDE","findings"),("ROADMAP","roadmap"),("EMPFEHLUNG","recommendation")]:
        if marker in u: return role
    return "other"


def main(argv:list[str])->int:
    if len(argv)!=5:
        print("FAIL: usage: create_customer_semantic_qa_manifest.py <pdf> <client-model.json> <scored-report.json> <out.json>",file=sys.stderr); return 1
    pdf,model,report,out=map(lambda x:Path(x).resolve(),argv[1:])
    if not pdf.is_file() or not model.is_file() or not report.is_file():
        print("FAIL: PDF/model/report missing",file=sys.stderr); return 1
    try:
        reader=PdfReader(str(pdf)); m=json.loads(model.read_text(encoding="utf-8")); r=json.loads(report.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {exc}",file=sys.stderr); return 1
    pages=[]
    for i,page in enumerate(reader.pages,1):
        text=page.extract_text() or ""
        pages.append({
            "page":i,
            "role":page_role(text,i),
            "checks":{k:False for k in PAGE_CHECKS},
            "notes":"",
        })
    payload={
        "schema_version":"1.1",
        "pdf_path":str(pdf.relative_to(out.parent)) if pdf.is_relative_to(out.parent) else pdf.name,"pdf_sha256":sha(pdf),
        "client_model_path":str(model.relative_to(out.parent)) if model.is_relative_to(out.parent) else model.name,"client_model_sha256":sha(model),
        "scored_report_path":str(report.relative_to(out.parent)) if report.is_relative_to(out.parent) else report.name,"scored_report_sha256":sha(report),
        "customer":str(m.get("meta",{}).get("customer",r.get("meta",{}).get("customer_name",""))),
        "page_count":len(pages),
        "inspection_status":"PENDING",
        "inspection_method":None,
        "inspected_by":None,
        "overall_checks":{k:False for k in OVERALL_CHECKS},
        "pages":pages,
        "review_questions":[
            "Würde der Kerninhalt ohne Firmenname/Logo noch konkrete Beobachtungen dieser Website enthalten?",
            "Kann ein Nicht-Fachmann je Prioritätsseite in einem Satz Problem und nächsten Schritt erklären?",
            "Sind direkt messbare oder zählbare Signale als Zahl/Visual sichtbar statt im Fließtext versteckt?",
            "Passt jedes Visual zur Aussage der Seite und zum kanonischen Audit?",
            "Sind die wichtigsten 3-4 Hebel des konkreten Kunden priorisiert statt generischer Agenturthemen?",
            "Ist die Kernaussage auf Seite 1 vollständig sichtbar und nicht auf eine Folgeseite abgeschnitten?",
            "Ist die Score-Darstellung exakt mit dem internen display_status konsistent?",
            "Zeigt jeder der vier Hebel Befund, geschäftliche Wirkung und nächsten Schritt?",
        ],
        "inspection_note":"Set PASS only after actual rendered-page review against both the client model and canonical scored audit. This file must not self-certify.",
    }
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"PASS: created PENDING semantic customer QA for {len(pages)} pages")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
