#!/usr/bin/env python3
"""Validate completed semantic customer QA; does not perform the inspection itself."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
from pypdf import PdfReader

OVERALL_BASE={"customer_specificity","plain_language_comprehension","scan_first_story","evidence_fidelity","priority_quality","quantitative_content_visualized","cross_page_coherence","actionability","no_generic_agency_copy","no_unsupported_business_claims"}
OVERALL_11=OVERALL_BASE|{"cover_message_complete","score_projection_correct","lever_business_impact_complete","privacy_claim_scope_correct","no_synthetic_metric_visuals"}
PAGE={"customer_specific","main_message_clear","scan_in_seconds","plain_language","evidence_faithful","visual_semantic_fit"}
METHODS={"agent_vision","human_review","hybrid"}

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(x:str)->int:print("FAIL: "+x,file=sys.stderr);return 1

def main(argv:list[str])->int:
    if len(argv)!=5:return fail("usage: validate_customer_semantic_qa.py <pdf> <client-model.json> <scored-report.json> <qa.json>")
    pdf,model,report,qa=map(lambda x:Path(x).resolve(),argv[1:])
    try:d=json.loads(qa.read_text(encoding="utf-8")); reader=PdfReader(str(pdf))
    except Exception as exc:return fail(str(exc))
    if d.get("schema_version") not in {"1.0","1.1"}:return fail("semantic QA schema_version must be 1.0 or 1.1")
    for key,path in [("pdf_sha256",pdf),("client_model_sha256",model),("scored_report_sha256",report)]:
        if d.get(key)!=sha(path):return fail(f"{key} not bound to current artifact")
    if d.get("page_count")!=len(reader.pages):return fail("semantic QA page_count mismatch")
    if d.get("inspection_status")!="PASS":return fail("inspection_status must be PASS after actual semantic inspection")
    if d.get("inspection_method") not in METHODS:return fail("inspection_method must be agent_vision, human_review or hybrid")
    if not str(d.get("inspected_by") or "").strip():return fail("inspected_by required")
    overall=d.get("overall_checks")
    required_overall = OVERALL_11 if d.get("schema_version")=="1.1" else OVERALL_BASE
    if not isinstance(overall,dict) or not required_overall.issubset(overall):return fail("overall semantic checks incomplete")
    bad=[k for k in required_overall if overall.get(k) is not True]
    if bad:return fail("failed overall semantic checks: "+", ".join(sorted(bad)))
    pages=d.get("pages")
    if not isinstance(pages,list) or len(pages)!=len(reader.pages):return fail("every page requires one semantic QA record")
    seen=set()
    for item in pages:
        if not isinstance(item,dict) or not isinstance(item.get("page"),int):return fail("invalid page record")
        seen.add(item["page"]); checks=item.get("checks")
        if not isinstance(checks,dict) or not PAGE.issubset(checks):return fail(f"page {item['page']} semantic checks incomplete")
        failed=[k for k in PAGE if checks.get(k) is not True]
        if failed:return fail(f"page {item['page']} failed semantic checks: "+", ".join(sorted(failed)))
    if seen!=set(range(1,len(reader.pages)+1)):return fail("semantic QA page numbering incomplete")
    print(f"PASS: semantic customer QA bound to final artifacts ({len(reader.pages)} pages)")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
