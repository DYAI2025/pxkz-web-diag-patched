#!/usr/bin/env python3
"""Fast deterministic E2E regression for the Pixelkiez business-first reporting stack."""
from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path

def run(args:list[str])->str:
    p=subprocess.run(args,text=True,capture_output=True,timeout=90)
    if p.returncode:
        raise RuntimeError(f"command failed {args}: {p.stderr[-2000:]} {p.stdout[-2000:]}")
    return p.stdout

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def main(argv:list[str])->int:
    if len(argv)!=2:
        print('FAIL: usage: run_business_first_reporting_evals.py <skill-dir>',file=sys.stderr);return 1
    root=Path(argv[1]).resolve(); py=sys.executable
    try:
        with tempfile.TemporaryDirectory(prefix='pxk-business-first-') as td:
            t=Path(td); scored=t/'scored.json'; analysis=t/'analysis_report.json'; md=t/'analysis_report.md'; plan=t/'visualization-plan.json'; model=t/'client-report-model.json'; visuals=t/'visuals'; vr=t/'visualization-render-receipt.json'; pdf=t/'customer_presentation.pdf'; pr=t/'presentation-render-receipt.json'; html=t/'customer_presentation.html'
            run([py,str(root/'scripts/compute_score.py'),str(root/'evals/fixtures/synthetic-report.json'),str(scored)])
            run([py,str(root/'scripts/build_internal_analysis_report.py'),str(scored),str(analysis)])
            run([py,str(root/'scripts/render_internal_analysis_markdown.py'),str(analysis),str(md)])
            run([py,str(root/'scripts/validate_internal_analysis_report.py'),str(analysis),str(scored),str(md)])
            run([py,str(root/'scripts/validate_analysis_report_completeness.py'),str(analysis),str(md),str(scored)])
            run([py,str(root/'scripts/build_visualization_plan.py'),str(scored),str(plan)])
            run([py,str(root/'scripts/validate_visualization_plan.py'),str(plan),str(scored)])
            pdata=json.loads(plan.read_text()); selected=[x for x in pdata['visuals'] if x.get('status')=='SELECTED']; selected_ids={x['template_id'] for x in selected}; excluded={x['template_id']:x['reason'] for x in pdata.get('excluded_candidates',[])}
            if not 4<=len(selected)<=7: raise RuntimeError('customer visual budget outside 4-7')
            if 'V12_AUDIT_COVERAGE' in selected_ids or excluded.get('V12_AUDIT_COVERAGE')!='INTERNAL_ONLY_NOT_CUSTOMER_VISIBLE': raise RuntimeError('coverage visual customer boundary failed')
            if len(pdata.get('top_levers',[]))!=4: raise RuntimeError('exactly four business levers required')
            if excluded.get('V04_FINDABILITY_BENCHMARK')!='BENCHMARK_CONTEXT_MISSING' or excluded.get('V05_RANKING_POSITION')!='SERP_QUERY_CONTEXT_MISSING': raise RuntimeError('benchmark/ranking fail-closed boundary failed')
            run([py,str(root/'scripts/build_client_report_model.py'),str(scored),str(model),'--visual-plan',str(plan)])
            run([py,str(root/'scripts/validate_client_report_model.py'),str(model)])
            run([py,str(root/'scripts/validate_customer_business_language.py'),str(model)])
            ad=json.loads(analysis.read_text())
            report={
              'status':'PASS','suite':'business-first-reporting','mandatory_product_outputs':['analysis_report.json','analysis_report.md','customer_presentation.pdf'],
              'metric_count':len(ad.get('metrics',[])),'selected_visual_count':len(selected),'selected_template_ids':sorted(selected_ids),'top_lever_count':4,'renderer':'SEPARATE_RENDER_PROOF_REQUIRED',
              'brand_font_status':'SEPARATE_RENDER_PROOF_REQUIRED','customer_language_firewall':'PASS','analysis_completeness':'PASS','coverage_visual_customer_status':'BLOCKED_INTERNAL_ONLY',
              'benchmark_without_context':'BLOCKED','ranking_without_context':'BLOCKED','unsafe_svg':'REJECTED_BY_DEDICATED_VALIDATOR','customer_release_ready_before_qa':False,
              'artifact_examples':{'analysis_sha256':sha(analysis),'model_sha256':sha(model)},
              'does_not_prove':['exact runtime font availability','live benchmark data','customer approval','commercial outcome']
            }
        (root/'reports/business-first-reporting-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('PASS: business-first reporting E2E')
        return 0
    except Exception as exc:
        (root/'reports/business-first-reporting-eval-results.json').write_text(json.dumps({'status':'FAIL','suite':'business-first-reporting','error':str(exc)},ensure_ascii=False,indent=2)+'\n')
        print('FAIL: '+str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main(sys.argv))
