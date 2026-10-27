#!/usr/bin/env python3
"""Validate non-compensatory final quality for one Pixelkiez customer presentation bundle."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from pypdf import PdfReader

def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd:list[str])->tuple[bool,str]:
    p=subprocess.run(cmd,text=True,capture_output=True)
    return p.returncode==0,(p.stdout or p.stderr).strip()
def visible(model:dict)->str:
    subset={"cover":model.get("cover"),"executive":model.get("executive"),"categories":model.get("categories"),"findings":[{k:f.get(k) for k in ("headline","observation","impact","action")} for f in model.get("findings",[]) if isinstance(f,dict)],"roadmap":model.get("roadmap"),"recommendation":model.get("recommendation"),"closing":model.get("closing")}
    return json.dumps(subset,ensure_ascii=False)
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("output_dir"); ap.add_argument("--json-out"); ap.add_argument("--allow-pending",action="store_true"); a=ap.parse_args()
    out=Path(a.output_dir).resolve(); report_path=Path(a.json_out).resolve() if a.json_out else out/"customer-presentation-quality-report.json"
    root=Path(__file__).resolve().parents[1]; gates=[]; errors=[]; pending=[]
    def gate(name:str, ok:bool, detail:str="", is_pending:bool=False):
        gates.append({"id":name,"status":"PENDING" if is_pending else ("PASS" if ok else "FAIL"),"detail":detail})
        if is_pending: pending.append(name)
        elif not ok: errors.append(name+(": "+detail if detail else ""))
    try:
        names=["customer_presentation.pdf","client-report-model.json","diagnosis-report.json","presentation-render-receipt.json","customer_presentation.visual-qa.json","customer_presentation.semantic-qa.json","visualization-plan.json"]
        missing=[n for n in names if not (out/n).is_file()]
        if missing: raise ValueError("missing artifacts: "+", ".join(missing))
        pdf=out/"customer_presentation.pdf"; modelp=out/"client-report-model.json"; scoredp=out/"diagnosis-report.json"
        model=json.loads(modelp.read_text(encoding="utf-8")); scored=json.loads(scoredp.read_text(encoding="utf-8")); receipt=json.loads((out/"presentation-render-receipt.json").read_text(encoding="utf-8")); vqa=json.loads((out/"customer_presentation.visual-qa.json").read_text(encoding="utf-8")); sqa=json.loads((out/"customer_presentation.semantic-qa.json").read_text(encoding="utf-8")); plan=json.loads((out/"visualization-plan.json").read_text(encoding="utf-8"))
        bound=(receipt.get("pdf_sha256")==sha(pdf) and receipt.get("model_sha256")==sha(modelp) and vqa.get("pdf_sha256")==sha(pdf) and sqa.get("pdf_sha256")==sha(pdf) and sqa.get("client_model_sha256")==sha(modelp) and sqa.get("scored_report_sha256")==sha(scoredp))
        gate("artifact_binding",bound,"all QA/render receipts must bind to final digests")
        status=str(scored.get("score_summary",{}).get("display_status") or "NO_SCORE"); raw=scored.get("score_summary",{}).get("score"); cover=model.get("cover",{})
        expected_label={"FULL_SCORE":"Pixelkiez Score","PARTIAL_SCORE":"Pixelkiez Bewertungsstand"}.get(status,"")
        expected_value=raw if status in {"FULL_SCORE","PARTIAL_SCORE"} and isinstance(raw,(int,float)) and not isinstance(raw,bool) else None
        gate("score_projection",cover.get("score_label")==expected_label and cover.get("score")==expected_value,f"status={status} expected_label={expected_label!r}")
        first=(PdfReader(str(pdf)).pages[0].extract_text() or "")
        verdict=" ".join(str(cover.get("verdict") or "").split()); customer=" ".join(str(model.get("meta",{}).get("customer") or "").split())
        cover_text=" ".join(first.split())
        cover_ok=bool(verdict and customer and customer in cover_text and all(token in cover_text for token in verdict.split()[:min(6,len(verdict.split()))]))
        cover_checks=vqa.get("cover_checks") if isinstance(vqa.get("cover_checks"),dict) else {}
        if vqa.get("inspection_status")!="PASS": gate("cover_integrity",False,"visual QA pending",is_pending=True)
        else: gate("cover_integrity",cover_ok and all(cover_checks.get(k) is True for k in ("full_takeaway_visible","score_projection_visible_when_required","no_cross_page_sentence_split")),"cover text + explicit visual checks")
        findings=[f for f in model.get("findings",[]) if isinstance(f,dict)]
        lever_ok=len(findings)==4 and all(str(f.get(k) or "").strip() for f in findings for k in ("observation","impact","action"))
        gate("four_lever_completeness",lever_ok,"exactly four levers with observation/impact/action")
        text=visible(model); actions=model.get("closing",{}).get("actions",[]) if isinstance(model.get("closing"),dict) else []
        sentence_ok="…" not in text and "..." not in text and len(actions)==4 and all(str(x).strip()[-1:] in ".!?" for x in actions if str(x).strip())
        gate("sentence_integrity",sentence_ok,"no truncation markers; four terminated closing actions")
        template=(root/"templates/presentation.html.j2").read_text(encoding="utf-8")
        gate("business_impact_visibility","Warum das zählt:" in template and "finding.impact" in template,"four-lever template must render impact")
        privacy_bad=re.search(r"(?:DSGVO[- ]?konform|rechtssicher|rechtskonform|Website ist rechtswidrig|versto(?:ß|ss)en definitiv|[0-9]+\s*%\s*(?:Rechtsverstoß|Illegalität)|erhalten\s+[0-9.]+\s*€\s*Strafe|Einwilligungen?.{0,30}(?:\bOK\b|\bklar\b|konform))",text,re.I)
        gate("privacy_claim_scope",privacy_bad is None,privacy_bad.group(0) if privacy_bad else "bounded")
        legal_meta=re.search(r"(?:\bILES\b|applicability_status|legal_exposure_band|statutory_maximum|expected_penalty|iles_points)",text,re.I)
        gate("legal_internal_metadata_leakage",legal_meta is None,legal_meta.group(0) if legal_meta else "bounded")
        sidecar=out/"impressum-compliance.json"
        if sidecar.is_file():
            ok,msg=run([sys.executable,str(root/"scripts/validate_impressum_projection.py"),str(sidecar),str(scoredp),str(modelp),str(pdf)])
            gate("legal_risk_projection_completeness",ok,msg)
        else:
            gate("legal_risk_projection_completeness",True,"not applicable: no bound Impressum sidecar")
        v03=[x for x in plan.get("visuals",[]) if isinstance(x,dict) and x.get("template_id")=="V03_TOP_LEVERS" and x.get("status")=="SELECTED"]
        synthetic=any(any(k in row for k in ("score","value","percent","magnitude")) for v in v03 for row in (v.get("data") if isinstance(v.get("data"),list) else []) if isinstance(row,dict))
        gate("no_synthetic_priority_magnitude",not synthetic,"V03 may contain rank but no magnitude field")
        page_count=len(PdfReader(str(pdf)).pages); gate("page_budget",page_count<=12,f"pages={page_count}")
        ok,msg=run([sys.executable,str(root/"scripts/validate_customer_business_language.py"),str(modelp),str(pdf)]); gate("customer_language_guardrails",ok,msg)
        if vqa.get("inspection_status")!="PASS": gate("visual_qa",False,"PENDING actual page inspection",is_pending=True)
        else:
            ok,msg=run([sys.executable,str(root/"scripts/validate_pdf_visual_qa.py"),str(pdf),str(out/"customer_presentation.visual-qa.json")]); gate("visual_qa",ok,msg)
        if sqa.get("inspection_status")!="PASS": gate("semantic_qa",False,"PENDING actual semantic inspection",is_pending=True)
        else:
            ok,msg=run([sys.executable,str(root/"scripts/validate_customer_semantic_qa.py"),str(pdf),str(modelp),str(scoredp),str(out/"customer_presentation.semantic-qa.json")]); gate("semantic_qa",ok,msg)
        quality_status="FAIL" if errors else ("PENDING_QA" if pending else "PASS")
        payload={"schema_version":"1.0","quality_contract_version":"1.0","quality_status":quality_status,"non_compensatory":True,"passed_hard_gates":sum(g["status"]=="PASS" for g in gates),"hard_gate_count":len(gates),"pending_gates":pending,"failed_gates":errors,"pdf_sha256":sha(pdf),"client_model_sha256":sha(modelp),"scored_report_sha256":sha(scoredp),"gates":gates}
        report_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if errors: print("FAIL: "+"; ".join(errors),file=sys.stderr); return 1
        if pending and not a.allow_pending: print("FAIL: quality gate pending actual QA: "+", ".join(pending),file=sys.stderr); return 1
        print(f"PASS: quality gate status={quality_status} hard_gates={len(gates)}")
        return 0
    except Exception as exc:
        payload={"schema_version":"1.0","quality_contract_version":"1.0","quality_status":"FAIL","non_compensatory":True,"failed_gates":[str(exc)],"gates":gates}
        report_path.parent.mkdir(parents=True,exist_ok=True); report_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("FAIL: "+str(exc),file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
