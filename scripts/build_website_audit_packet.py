#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
from build_elevenlabs_batch_csv import select_hooks

ROOT=Path(__file__).resolve().parent.parent
SCHEMA=ROOT/'schemas/website-audit-packet.schema.json'

def digest(data:dict)->str:
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main(argv:list[str])->int:
    if len(argv)!=3:
        print('FAIL: usage: build_website_audit_packet.py <diagnosis-report-scored.json> <website-audit-packet.json>',file=sys.stderr); return 1
    report=json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    meta=report.get('meta',{}); score=report.get('score_summary',{}); findings=[f for f in report.get('findings',[]) if isinstance(f,dict)]
    strengths=[]
    for f in findings:
        if f.get('severity')=='positive' and len(strengths)<3:
            strengths.append({'finding_id':f.get('id'),'observation':f.get('client_observation') or f.get('observation'),'confidence':f.get('confidence')})
    priorities=[]
    sev={'critical':0,'high':1,'medium':2,'low':3}
    for f in sorted([x for x in findings if x.get('severity')!='positive'], key=lambda x:(sev.get(str(x.get('severity')),9),-int(x.get('confidence',0)),str(x.get('id',''))))[:4]:
        priorities.append({'finding_id':f.get('id'),'severity':f.get('severity'),'observation':f.get('client_observation') or f.get('observation'),'impact':f.get('client_impact') or f.get('business_relevance',{}).get('text'),'action':f.get('client_action') or f.get('recommendation',{}).get('action'),'confidence':f.get('confidence')})
    hooks=[]
    for h in select_hooks(report)[:3]:
        hooks.append({'finding_id':h.get('id'),'dimension':h.get('dimension'),'priority':h.get('priority'),'evidence_class':h.get('evidence_class'),'observation':h.get('observation'),'evidence_pointer':h.get('evidence_pointer'),'confidence':h.get('confidence',0),'selector_score':h.get('selector_score') if h.get('selector_score') is not None else h.get('confidence',0),'spoken':h.get('spoken'),'possible_relevance':h.get('possible_relevance'),'prohibited_claims':str(h.get('prohibited_claims','')).split('|') if h.get('prohibited_claims') else []})
    packet={'packet_version':'1.0','audit_id':str(meta.get('audit_id') or 'AUD-PXK-'+digest(report)[:12].upper()),'company':str(meta.get('customer_name') or report.get('public_business',{}).get('display_name') or ''),'website':str(meta.get('audited_url') or ''),'audit_date':str(meta.get('audit_date') or ''),'score_state':{'display_status':score.get('display_status'),'score':score.get('score'),'coverage_percent':score.get('coverage_percent'),'category_scores':score.get('category_scores',[]),'score_gate_reasons':score.get('score_gate_reasons',[])},'limitations':[str(x) for x in report.get('limitations',[]) if str(x).strip()],'strengths':strengths,'remediation_priorities':priorities,'conversation_hooks':hooks,'source_report_digest':digest(report)}
    schema=json.loads(SCHEMA.read_text(encoding='utf-8')); Draft202012Validator(schema).validate(packet)
    Path(argv[2]).write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"PASS: provider-neutral audit packet priorities={len(priorities)} hooks={len(hooks)}")
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
