#!/usr/bin/env python3
"""Deterministic evals for Pixelkiez measurement enrichment and customer warning semantics."""
from __future__ import annotations
import copy, json, subprocess, sys, tempfile
from pathlib import Path

from customer_status import customer_status
from measurement_adapters import parse_dataforseo

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable

def run(args:list[str])->subprocess.CompletedProcess[str]:
    return subprocess.run(args,text=True,capture_output=True,cwd=ROOT)

def main()->int:
    checks={}
    with tempfile.TemporaryDirectory(prefix='pxk-enrich-eval-') as td:
        td=Path(td); enrichment=td/'enrichment.json'
        p=run([PY,'scripts/collect_measurement_enrichment.py','https://example.com',str(enrichment),'--config','evals/fixtures/measurement-enrichment-config.json','--fixture-bundle','evals/fixtures/measurement-provider-responses.json','--offline'])
        checks['fixture_collection_pass']=p.returncode==0
        v=run([PY,'scripts/validate_measurement_enrichment.py',str(enrichment)])
        checks['schema_truth_validation_pass']=v.returncode==0
        data=json.loads(enrichment.read_text()) if enrichment.exists() else {'metrics':[]}
        mids={m.get('id') for m in data.get('metrics',[]) if isinstance(m,dict)}
        checks['provider_families_present']=all(x in mids for x in ['SERP_CURRENT_POSITION','SERP_CURRENT_PAGE','GSC_AVG_POSITION','GA4_ACTIVE_USERS','GA4_FORM_SUBMITS','PSI_LCP_LAB_MS','CRUX_LCP_P75_MS'])
        # Explicit page must not be derived from position.
        dfs=json.loads((ROOT/'evals/fixtures/measurement-provider-responses.json').read_text())['dataforseo']['queries']['blitzschutz ludwigsfelde']
        no_page=copy.deepcopy(dfs); no_page['tasks'][0]['result'][0]['items'][0].pop('page',None)
        parsed=parse_dataforseo(no_page,'https://example.com','blitzschutz ludwigsfelde',requested_location='Berlin,Germany',requested_device='mobile',source_type='FIXTURE_REPLAY')
        checks['serp_page_fail_closed']=not any(x['id']=='SERP_CURRENT_PAGE' for x in parsed) and any(x['id']=='SERP_CURRENT_POSITION' for x in parsed)
        # Query-specific current SERP and Search Console average stay separate.
        serp=next(m for m in data['metrics'] if m['id']=='SERP_CURRENT_POSITION' and m.get('query')=='blitzschutz ludwigsfelde')
        gsc=next(m for m in data['metrics'] if m['id']=='GSC_AVG_POSITION' and m.get('query')=='blitzschutz ludwigsfelde')
        checks['serp_vs_gsc_truth_separated']=serp['value']==18 and gsc['value']==16.7 and serp['source_provider']!=gsc['source_provider']
        # CTA/phone proxies must preserve non-lead boundary.
        phone=next(m for m in data['metrics'] if m['id']=='GA4_PHONE_CLICKS')
        checks['phone_click_not_lead']=('weder einen anruf' in phone['claim_boundary'].casefold() and 'lead' in phone['claim_boundary'].casefold())
        # Four-state status contract: concrete weak privacy => explicit ACTION/X; not assessed => neutral.
        action=customer_status({'measurement_class':'observed','status':'weak','score':25})
        unknown=customer_status({'measurement_class':'not_assessed','status':'not_assessed','score':None})
        checks['warning_semantics_action_x']=action['key']=='ACTION' and action['label']=='Handlungsbedarf' and action['symbol']=='X'
        checks['unknown_not_red']=unknown['key']=='UNASSESSED' and unknown['tone']=='neutral'
        # Attach enrichment to scored 48-metric report and verify score core remains 48 and value unchanged.
        scored=td/'scored.json'; enriched=td/'enriched.json'
        p=run([PY,'scripts/compute_score.py','evals/fixtures/synthetic-report.json',str(scored)])
        base=json.loads(scored.read_text()) if scored.exists() else {}
        p2=run([PY,'scripts/attach_measurement_enrichment.py',str(scored),str(enrichment),str(enriched)])
        ed=json.loads(enriched.read_text()) if enriched.exists() else {}
        checks['score_core_unchanged']=p.returncode==0 and p2.returncode==0 and len(ed.get('metrics',[]))==48 and ed.get('score_summary',{}).get('score')==base.get('score_summary',{}).get('score')
        # V10 privacy weakness renders as action state and V05 uses measured SERP.
        weak=copy.deepcopy(ed)
        for m in weak.get('metrics',[]):
            if m.get('id')=='TRUST-02':
                m['measurement_class']='observed'; m['status']='weak'; m['score']=25; m['value']='privacy/consent surface needs action'
        weakp=td/'weak.json'; weakp.write_text(json.dumps(weak,ensure_ascii=False,indent=2)+'\n')
        plan=td/'plan.json'; bp=run([PY,'scripts/build_visualization_plan.py',str(weakp),str(plan)])
        pl=json.loads(plan.read_text()) if plan.exists() else {'visuals':[]}
        v10=next((v for v in pl.get('visuals',[]) if v.get('template_id')=='V10_TRUST_MATRIX' and v.get('status')=='SELECTED'),None)
        prow=next((r for r in (v10 or {}).get('data',[]) if 'Datenschutz' in str(r.get('signal'))),{})
        checks['v10_privacy_action_visible']=bp.returncode==0 and prow.get('status')=='Handlungsbedarf' and prow.get('symbol')=='X' and prow.get('tone')=='bad'
        checks['serp_visual_selected']=any(v.get('template_id')=='V05_RANKING_POSITION' and v.get('status')=='SELECTED' for v in pl.get('visuals',[]))
        # v8 closing must not contain old negative limits page.
        client=td/'client.json'; bc=run([PY,'scripts/build_client_report_model.py',str(ed),str(client),'--visual-plan',str(plan)])
        # use matching plan digest: rebuild against ed for strict validation
        plan2=td/'plan2.json'; run([PY,'scripts/build_visualization_plan.py',str(enriched),str(plan2)])
        bc=run([PY,'scripts/build_client_report_model.py',str(enriched),str(client),'--visual-plan',str(plan2)])
        cd=json.loads(client.read_text()) if client.exists() else {}
        checks['closing_replaces_limitations']=bool(bc.returncode==0 and 'closing' in cd and 'client_limits' not in cd and cd.get('closing',{}).get('cta'))
        checks['closing_surfaces_real_measurements']=bool(len(cd.get('closing',{}).get('measurement_highlights',[]))==3 and any('Position 18' in x.get('value','') for x in cd.get('closing',{}).get('measurement_highlights',[])))
        if bc.returncode != 0:
            report_diag = {'client_stdout': bc.stdout, 'client_stderr': bc.stderr}
        else:
            report_diag = {}
    status='PASS' if all(checks.values()) else 'FAIL'
    report={'schema_version':'1.0','status':status,'checks':checks,'diagnostics':locals().get('report_diag',{}),'browser_runtime':'SEPARATE_RUNTIME_PROBE','note':'Provider/API parsing is deterministic fixture replay; live credentials/provider responses are not claimed by this eval.'}
    (ROOT/'reports/measurement-enrichment-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if status!='PASS':
        print('FAIL: '+json.dumps({k:v for k,v in checks.items() if not v})); return 1
    print(f'PASS: measurement enrichment evals checks={len(checks)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
