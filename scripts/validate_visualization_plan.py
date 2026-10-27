#!/usr/bin/env python3
"""Validate visualization plan schema, references and benchmark truth boundaries."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from visualization_policy import CUSTOMER_MAX_VISUALS, CUSTOMER_MIN_VISUALS  # noqa: E402

APPROVED={
"V01_OVERALL_SCORE","V02_CATEGORY_BARS","V03_TOP_LEVERS","V04_FINDABILITY_BENCHMARK","V05_RANKING_POSITION","V06_QUERY_COVERAGE","V07_PERFORMANCE_THRESHOLD","V08_AI_ANSWERABILITY","V09_AGENT_READINESS","V10_TRUST_MATRIX","V11_SEVERITY_DISTRIBUTION","V12_AUDIT_COVERAGE","V13_IMPACT_EFFORT","V14_REPEAT_AUDIT","D01_PROCESS_FLOW"}
BENCH={"V04_FINDABILITY_BENCHMARK"}
CUSTOMER_FORBIDDEN={"V01_OVERALL_SCORE","V12_AUDIT_COVERAGE"}

def fail(m): print('FAIL: '+m,file=sys.stderr); return 1

def main(argv):
    if len(argv)!=3:return fail('usage: validate_visualization_plan.py <plan.json> <report.json>')
    planp,reportp=map(lambda x:Path(x).resolve(),argv[1:]); root=Path(__file__).resolve().parents[1]
    try:
        plan=json.loads(planp.read_text(encoding='utf-8')); report=json.loads(reportp.read_text(encoding='utf-8'))
        schema=json.loads((root/'schemas/visualization-plan.schema.json').read_text(encoding='utf-8'))
        errs=list(Draft202012Validator(schema).iter_errors(plan))
        if errs:return fail('schema: '+errs[0].message)
        if plan['source_report_sha256']!=hashlib.sha256(reportp.read_bytes()).hexdigest():return fail('stale source report digest')
        if plan['brand_token_sha256']!=hashlib.sha256((root/'assets/brand-tokens.json').read_bytes()).hexdigest():return fail('stale brand token digest')
        mids={str(x.get('id')) for x in report.get('metrics',[])}
        fids={str(x.get('id')) for x in report.get('findings',[])}
        legal_refs=set()
        for finding in report.get('findings',[]):
            if not isinstance(finding,dict):
                continue
            risk=finding.get('customer_risk') if isinstance(finding.get('customer_risk'),dict) else {}
            if risk.get('source')=='impressum_compliance':
                legal_refs.update(str(x) for x in risk.get('legal_metric_refs',[]) if str(x).startswith('LEGAL-IMP-'))
        selected=[x for x in plan['visuals'] if x['status']=='SELECTED']
        if len(selected)<CUSTOMER_MIN_VISUALS:return fail(f'customer plan requires at least {CUSTOMER_MIN_VISUALS} selected visuals')
        if len(selected)>CUSTOMER_MAX_VISUALS:return fail(f'customer plan may contain at most {CUSTOMER_MAX_VISUALS} selected visuals')
        if len({x['id'] for x in selected})!=len(selected):return fail('duplicate visual IDs')
        if any(x.get("template_id") in CUSTOMER_FORBIDDEN for x in selected):return fail("customer plan selected internal or redundant score/coverage visual")
        for v in plan['visuals']:
            if v['template_id'] not in APPROVED:return fail('unapproved template '+v['template_id'])
            for ref in v['metric_refs']:
                if ref.startswith(('SCORE:','CATEGORY:')):continue
                if ref.startswith('LEGAL-IMP-') and ref in legal_refs:continue
                if ref not in mids:return fail(f"{v['id']} unknown metric ref {ref}")
            for ref in v['finding_refs']:
                if ref not in fids:return fail(f"{v['id']} unknown finding ref {ref}")
            if not v['population'].strip() or not v['method'].strip() or not v['does_not_prove'].strip():return fail(f"{v['id']} evidence boundary incomplete")
            visible_fields=[v.get('title',''),v.get('subtitle',''),v.get('population',''),v.get('does_not_prove','')]
            if any('…' in str(x) or '...' in str(x) for x in visible_fields):return fail(f"{v['id']} visible text contains truncation marker")
            if v['template_id']=='V03_TOP_LEVERS':
                rows=v.get('data') if isinstance(v.get('data'),list) else []
                if len(rows)!=4:return fail(f"{v['id']} top-lever visual requires exactly four rows")
                for idx,row in enumerate(rows,1):
                    label=' '.join(str(row.get('label') or '').split()) if isinstance(row,dict) else ''
                    if not label or len(label)>130:return fail(f"{v['id']} lever label {idx} invalid length")
                    if '…' in label or '...' in label:return fail(f"{v['id']} lever label {idx} is truncated")
            if v['template_id'] in BENCH:
                b=report.get('benchmark_data')
                if not isinstance(b,dict) or not all(b.get(k) for k in ('measured_at','method','location','entities')):return fail(f"{v['id']} benchmark context missing")
            if v['template_id']=='V05_RANKING_POSITION':
                rows=v.get('data') if isinstance(v.get('data'),list) else []
                if not rows or not all(isinstance(r,dict) and r.get('query') and isinstance(r.get('position'),int) for r in rows):
                    return fail(f"{v['id']} ranking rows require query and integer position")
                enrichment=report.get('measurement_enrichment') if isinstance(report.get('measurement_enrichment'),dict) else {}
                em=[x for x in enrichment.get('metrics',[]) if isinstance(x,dict) and x.get('id')=='SERP_CURRENT_POSITION' and x.get('status') in {'MEASURED','OBSERVED'}]
                if em:
                    for row in rows:
                        match=next((x for x in em if x.get('query')==row.get('query') and int(x.get('value'))==int(row.get('position'))),None)
                        if not match:return fail(f"{v['id']} ranking row lacks measured enrichment source: {row.get('query')}")
                        if not all(match.get(k) for k in ('location','device','observed_at','source_provider')):
                            return fail(f"{v['id']} ranking enrichment context incomplete: {row.get('query')}")
                else:
                    b=report.get('benchmark_data')
                    if not isinstance(b,dict) or not all(b.get(k) for k in ('measured_at','method','location')):
                        return fail(f"{v['id']} ranking context missing")
        print(f"PASS: visualization plan selected={len(selected)} approved/referential/evidence-bound")
        return 0
    except Exception as e:return fail(str(e))
if __name__=='__main__':raise SystemExit(main(sys.argv))
