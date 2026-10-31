#!/usr/bin/env python3
"""Plan all canonical Core metrics; capture real bounded raw evidence and immutable run-scoped receipts.

LIVE does not assign scores without a site-specific rubric assessment. No forms, private
endpoints, paid API calls, or auth bypass. Partial runs remain explicitly open.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core_capture import browser_capture,check_public,google_capture,http_capture,lighthouse_capture,normalize_exception,now
from core_execution_gate import CLOSED,validate_execution
from validate_metric_execution_routes import load_checked

BUNDLE_NAME='core-execution-bundle.json'

def atomic(path:Path,obj:Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def artifact(run_dir:Path,kind:str,data:bytes)->dict:
    if not isinstance(data,bytes) or not data:raise ValueError('EMPTY_RAW_ARTIFACT')
    digest=sha(data)
    rel=f'evidence/raw/{kind}-{digest[:32]}.bin'
    dest=run_dir/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        if dest.read_bytes()!=data:raise ValueError('RAW_ARTIFACT_HASH_COLLISION')
    else:
        dest.write_bytes(data)
    return {'path':rel,'sha256':digest,'bytes':len(data),'kind':kind}

def _outcome(receipt:dict,opts:dict,run_dir:Path,cache:dict)->dict:
    route=opts['route'];adapter=route['adapter'];mid=opts['metric_id']
    if route['permission']=='owner_authorized' and not opts['owner_authorized']:
        return {'outcome':'POLICY_BLOCKED','observed_url':opts['url'],'artifacts':[('tool_log',b'POLICY_BOUNDARY: no owner authorization for private measurements; no endpoint requested')],
                'tool_name':'permission-boundary','tool_version':'1.0','exit_code':77,'reason':'Owner data not authorized; no outbound private request'}
    if route['implementation_status'] in {'MISSING_CORE_ADAPTER','MISSING_MACHINE_COLLECTOR','MISSING_AXE_OR_BRIDGE','MISSING_METRIC_SPECIFIC_EVALUATOR','EXISTING_NONCORE_ONLY','AUTH_REQUIRED_NONCORE_ONLY'}:
        return {'outcome':'IMPLEMENTATION_GAP','observed_url':opts['url'],
                'artifacts':[('tool_log',f"IMPLEMENTATION_GAP {mid} {route['method_id']}: existing capability lacks verified Core binding".encode())],
                'tool_name':'route-implementation-preflight','tool_version':'1.0','exit_code':78,'reason':f"{route['implementation_status']}; not an executed metric measurement"}

    if opts['offline']:
        return {'outcome':'CAPABILITY_UNAVAILABLE','observed_url':opts['url'],'artifacts':[('tool_log',b'OFFLINE: network capture not attempted')],
                'tool_name':'runtime-preflight','tool_version':'1.0','exit_code':127,'reason':'Offline mode disables live collection; remains pending'}
    if adapter=='PAGESPEED_API' or adapter=='PUBLIC_CRUX':
        if not opts['allow_api'] or not os.getenv('PIXELKIEZ_PAGESPEED_API_KEY'):
            return {'outcome':'CAPABILITY_UNAVAILABLE','observed_url':opts['url'],
                    'artifacts':[('tool_log',b'API disabled or PIXELKIEZ_PAGESPEED_API_KEY not supplied; no request')],
                    'tool_name':'api-capability-preflight','tool_version':'1.0','exit_code':127,'reason':'No authorized API invocation'}
    if adapter=='LIGHTHOUSE_CLI':
        if not opts['allow_lighthouse'] or not shutil.which('lighthouse'):
            return {'outcome':'CAPABILITY_UNAVAILABLE','observed_url':opts['url'],
                    'artifacts':[('tool_log',b'local Lighthouse CLI missing or not enabled; no process executed')],
                    'tool_name':'cli-capability-preflight','tool_version':'1.0','exit_code':127,'reason':'Local Lighthouse is not executable in this run'}
    if adapter=='PUBLIC_BROWSER':
        if not importlib.util.find_spec('playwright'):
            return {'outcome':'CAPABILITY_UNAVAILABLE','observed_url':opts['url'],
                    'artifacts':[('tool_log',b'playwright import not found')],
                    'tool_name':'browser-capability-preflight','tool_version':'1.0','exit_code':127,'reason':'No Playwright installation'}
        from browser_measurements import _chromium_path
        if not _chromium_path():
            return {'outcome':'CAPABILITY_UNAVAILABLE','observed_url':opts['url'],
                    'artifacts':[('tool_log',b'Chromium executable not found')],
                    'tool_name':'browser-capability-preflight','tool_version':'1.0','exit_code':127,'reason':'No Chromium binary'}
    if adapter in {'PUBLIC_SEARCH','MANUAL_EVIDENCE','OWNER_EXPORT'}:
        return {'outcome':'IMPLEMENTATION_GAP','observed_url':opts['url'],
                'artifacts':[('tool_log',f'{adapter}: no authorized Core direct collector; manual/paid step not triggered'.encode())],
                'tool_name':'route-implementation-preflight','tool_version':'1.0','exit_code':78,'reason':'No direct Core collector; external evidence must be audited separately'}
    factor='desktop' if mid=='PERF-03' else 'mobile'
    key=(adapter,opts['url'],factor) if adapter in {'PAGESPEED_API','LIGHTHOUSE_CLI'} else (adapter,opts['url'])
    if key in cache:return cache[key]
    try:
        if adapter=='PUBLIC_HTTP': result=http_capture(opts['url'])
        elif adapter=='PUBLIC_BROWSER':result=browser_capture(opts['url'])
        elif adapter=='LIGHTHOUSE_CLI':result=lighthouse_capture(opts['url'],factor)
        elif adapter in {'PUBLIC_CRUX','PAGESPEED_API'}:result=google_capture(opts['url'],adapter,factor)
        else:raise RuntimeError(f'Unknown executor: {adapter}')
    except Exception as exc:
        message=normalize_exception(exc)
        result={'outcome':'TOOL_FAILURE','observed_url':opts['url'],'artifacts':[('tool_log',message.encode('utf-8'))],
                'tool_name':f'{adapter.lower()}-executor','tool_version':sys.version.split()[0], 'exit_code':1,'reason':message}
    cache[key]=result
    return result


def create_receipt(run_dir:Path,execution_run_id:str,route:dict,mid:str,opts:dict,cache:dict)->tuple[dict,str]:
    started=now()
    result=_outcome({},dict(opts,route=route,metric_id=mid),run_dir,cache)
    finished=now()
    artifacts=[artifact(run_dir,k,data) for k,data in result['artifacts']]
    # No env vars, API keys, cookies, private response headers or full command line enter the receipt.
    rid='A-'+uuid.uuid4().hex.upper()
    receipt={'receipt_version':'1.0','producer':'pixelkiez.core-runner.v1','receipt_id':rid,
        'execution_run_id':execution_run_id,'metric_id':mid,'route_id':route['route_id'],
        'method_id':route['method_id'],'method_version':route['method_version'],'adapter':route['adapter'],
        'measurement_class':route['measurement_class'],'source_family':route['source_family'],
        'target_url':opts['url'],'observed_url':result['observed_url'],
        'started_at':started,'finished_at':finished,
        'tool':{'name':result['tool_name'],'version':result['tool_version'],'invocation':f"collector:{route['adapter']}/{route['method_id']}",
                'exit_code':result['exit_code']},
        'configuration':{'visual_claim':route['adapter']=='PUBLIC_BROWSER','device':'desktop' if mid=='PERF-03' else 'mobile','no_form_submission':True},
        'outcome':result['outcome'],'artifacts':artifacts,
        'scope':{'url_scope':result['observed_url'],'page_sample':[result['observed_url']]},
        'limits':{'timeout_seconds':20,'max_response_bytes':1048576,'max_pages':5},
        'context_params':{'measurement_class':route['measurement_class'],'permission':route['permission']},
        'reason':result['reason']}
    rel=f'evidence/receipts/{mid}-{route["route_id"]}.json'
    atomic(run_dir/rel,receipt)
    return receipt,rel


def execute_metric(run_dir:Path,run_id:str,metric:dict,route_entry:dict,opts:dict,cache:dict,assessment:dict|None)->tuple[dict,dict]:
    attempts=[];refs=[];skipped=[]
    routes=[route_entry['primary'],*route_entry['alternatives']]
    for idx,route in enumerate(routes):
        if idx>0 and attempts and attempts[-1]['outcome']=='SUCCESS_RAW':
            skipped.extend({'route_id':r['route_id'],'reason':'NOT_NEEDED_PRIMARY_SUCCEEDED'} for r in routes[idx:]);break
        if idx>0 and route.get('score_equivalence')=='NOT_EQUIVALENT_FOR_RENDERED_CLAIMS':
            skipped.append({'route_id':route['route_id'],'reason':'NOT_EQUIVALENT_FOR_RENDERED_CLAIMS'});continue
        receipt,rel=create_receipt(run_dir,run_id,route,metric['id'],opts,cache)
        attempts.append(receipt);refs.append(rel)
    # An implementation gap is open; no fake terminal unavailable status.
    outcomes=[x['outcome'] for x in attempts]
    successes=[x for x in attempts if x['outcome'] in {'SUCCESS_RAW','SUCCESS_VERIFIED'}]
    if successes:
        state='ATTEMPTED'
    elif outcomes and outcomes[-1]=='POLICY_BLOCKED' and route_entry['permission_boundary'] in {'owner_authorized','user_authorized_private'}:
        state='VERIFIED_POLICY_BLOCKED'
    elif outcomes and outcomes[-1]=='SOURCE_ABSENT' and attempts[-1]['adapter'] in {'PUBLIC_CRUX','PUBLIC_SEARCH','OWNER_EXPORT'}:
        state='VERIFIED_SOURCE_ABSENT'
    elif 'IMPLEMENTATION_GAP' in outcomes:
        state='PENDING'
    elif 'TOOL_FAILURE' in outcomes:
        state='VERIFIED_TOOL_FAILURE'
    elif outcomes and set(outcomes)=={'CAPABILITY_UNAVAILABLE'} and not opts['offline']:
        state='VERIFIED_UNAVAILABLE'
    else:state='PENDING'
    if state in {'VERIFIED_TOOL_FAILURE','VERIFIED_UNAVAILABLE'} and any(x['reason']=='IMPLEMENTATION_GAP' for x in skipped):
        state='PENDING'
    if successes and assessment is not None:
        score_status=assessment.get('product_status')
        registry_status={'strong','minor_gaps','mixed','weak','blocking'}
        if (score_status in registry_status and isinstance(assessment.get('value'),dict)
            and isinstance(assessment.get('rubric_observation'),str) and len(assessment['rubric_observation'].strip())>=12
            and isinstance(assessment.get('rubric_reason'),str) and len(assessment['rubric_reason'].strip())>=12):
            state='VERIFIED_RESULT'
        else:raise ValueError(f"{metric['id']}: USER_ASSESSMENT_NOT_COMPLETE")
    proof={'completion_state':state,'attempt_receipts':refs,'fallback_evaluations':skipped,'fallback_slots_unavailable':route_entry['unavailable_fallback_slots'],'assessment':assessment if state=='VERIFIED_RESULT' else None}
    best=successes[-1] if successes else (attempts[-1] if attempts else None)
    sf=best['source_family'] if best else route_entry['primary']['source_family']
    score=state=='VERIFIED_RESULT'
    if score:
        evidid=f'E-{int(opts["metric_index"]):03d}'
        raw=next(a for a in best['artifacts'] if a['kind']!='tool_log')
        evidence={'id':evidid,'source_family':sf,'target_url':opts['url'],'status':'OBSERVED',
                  'evidence_grade':metric['max_evidence_grade'],'digest':raw['sha256'],
                  'reference':raw['path'],'claim_boundary':'raw page or provider sample, assessment rubric limited to examined page',
                  'raw_provider_payload_present':False}
        refs_score=[evidid]
    else:evidence=None;refs_score=[]
    exc_to_base={'VERIFIED_POLICY_BLOCKED':'UNAVAILABLE','VERIFIED_TOOL_FAILURE':'ERROR','VERIFIED_SOURCE_ABSENT':'UNAVAILABLE','VERIFIED_UNAVAILABLE':'UNAVAILABLE','VERIFIED_NOT_APPLICABLE':'NOT_APPLICABLE','EVIDENCE_CONFLICT':'CONFLICT'}
    state_base=('OBSERVED' if best and best['measurement_class'] not in {'lab','field'} else 'MEASURED') if score else exc_to_base.get(state,'PENDING')
    reason_codes=[] if score else [ {'ERROR':'EXECUTION_ERROR','UNAVAILABLE':'EVIDENCE_UNAVAILABLE','CONFLICT':'EVIDENCE_CONFLICT','NOT_APPLICABLE':'NOT_APPLICABLE','PENDING':'EXECUTION_PENDING'}.get(state_base,'EXECUTION_PENDING') ]
    return {
        'metric_id':metric['id'],'target_url':opts['url'],'source_family':sf,'execution_state':state_base,
        'evidence_grade':metric['max_evidence_grade'] if score else 'E8',
        'value':assessment['value'] if score else None,'unit':assessment.get('unit') if score else None,
        'evidence_refs':refs_score,'source_or_method':best['method_id'] if best else route_entry['primary']['method_id'],
        'limitation':metric['limitation'],'product_status':assessment['product_status'] if score else None,
        'threshold_source':assessment.get('threshold_source') if score else None,
        'confidence':int(assessment.get('confidence',2)) if score else 1,'observed_at':now() if attempts else None,
        'reason_codes':reason_codes,'note':f'{state}: {len(attempts)} receipt-backed route checks',
        'raw_provider_payload_present':False,'execution_proof':proof
    },evidence


def probe_capabilities(root:Path,opts:dict)->dict:
    caps=json.loads((root/'assets/capability-registry.json').read_text())['capabilities']
    mapping={'public_http_fetch':'PUBLIC_HTTP','html_inspection':'PUBLIC_HTTP','crawl_sample':'PUBLIC_HTTP','structured_data_inspection':'PUBLIC_HTTP',
    'header_inspection':'PUBLIC_HTTP','asset_inspection':'PUBLIC_HTTP','content_inspection':'PUBLIC_HTTP',
    'public_page_render':'PUBLIC_BROWSER','accessibility_manual_sample':'PUBLIC_BROWSER','accessibility_automation':'PUBLIC_BROWSER',
    'performance_field':'PUBLIC_CRUX','performance_lab':'LIGHTHOUSE_CLI','search_sample':'PUBLIC_SEARCH','private_measurement_export':'OWNER_EXPORT'}
    installed_playwright=importlib.util.find_spec('playwright') is not None
    try:
        from browser_measurements import _chromium_path
        chromium=_chromium_path()
    except Exception:chromium=None
    browser_test=subprocess.run([chromium,'--version'],capture_output=True,text=True,timeout=8) if chromium else None
    rows=[]
    for cap in caps:
        adapter=mapping[cap['id']]
        installed=adapter=='PUBLIC_HTTP' or adapter=='PUBLIC_BROWSER' and installed_playwright and chromium is not None or adapter=='LIGHTHOUSE_CLI' and shutil.which('lighthouse') is not None or adapter=='PUBLIC_CRUX' and bool(os.getenv('PIXELKIEZ_PAGESPEED_API_KEY'))
        auth=(not opts['offline']) and (adapter not in {'OWNER_EXPORT','PUBLIC_CRUX','LIGHTHOUSE_CLI'} or adapter=='PUBLIC_CRUX' and opts['allow_api'] or adapter=='LIGHTHOUSE_CLI' and opts['allow_lighthouse'])
        invocable=bool(installed) and (adapter!='PUBLIC_BROWSER' or bool(browser_test and browser_test.returncode==0))
        rows.append({'capability_id':cap['id'],'adapter':adapter,'installed':bool(installed),'invocable':invocable,'authorized':bool(auth),
            'verified_success':False,'test_invocation':f'{adapter} capability check only','exit_code':0 if invocable else 127,
            'tool_version':(browser_test.stdout.strip() if browser_test and adapter=='PUBLIC_BROWSER' else sys.version.split()[0] if adapter=='PUBLIC_HTTP' else 'not_executed'),
            'evidence_files':[],'limits':'Preflight cannot prove target success; verified_success set only from captured receipt.'})
    return {'schema_version':'1.0','target_url':opts['url'],'capabilities':rows,'count':len(rows),'does_not_prove':['tool success without executed collection','authorized owner access']}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',required=True);p.add_argument('--output',required=True)
    p.add_argument('--offline',action='store_true');p.add_argument('--allow-api',action='store_true')
    p.add_argument('--allow-lighthouse',action='store_true');p.add_argument('--owner-authorized',action='store_true')
    p.add_argument('--assessments',help='Optional site-specific scored metric rubrics; not proof by itself')
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    try:
        catalog=load_checked(root);url=a.target
        if not a.offline:check_public(url)
        out=Path(a.output).resolve()
        if out.exists() and any(out.iterdir()):raise ValueError('RUN_DIR_NOT_EMPTY: no overwrite/resume without separately verified recovery')
        out.mkdir(parents=True,exist_ok=True)
        reg=json.loads((root/'assets/measurement-registry.json').read_text())['metrics']
        config=dict(url=url,offline=a.offline,allow_api=a.allow_api,allow_lighthouse=a.allow_lighthouse,owner_authorized=a.owner_authorized)
        if a.owner_authorized:raise ValueError('OWNER_EXPORT_NOT_IMPLEMENTED: no private credentials or owner data accepted in this patch')
        assessments=json.loads(Path(a.assessments).read_text()) if a.assessments else {}
        if not isinstance(assessments,dict) or set(assessments)-{m['id'] for m in reg}:
            raise ValueError('ASSESSMENT_ID_NOT_REGISTERED')
        run_id='PXK-'+uuid.uuid4().hex[:20]
        preflight=probe_capabilities(root,config)
        for cap in preflight['capabilities']:
            data=json.dumps({k:v for k,v in cap.items() if k!='evidence_files'},ensure_ascii=False,sort_keys=True).encode('utf-8')
            cap['evidence_files']=[artifact(out,'tool_log',data)]
        atomic(out/'capability-preflight.json',preflight)
        cache={};results=[];evidence=[];routes={r['metric_id']:r for r in catalog['metrics']}
        for i,metric in enumerate(reg,1):
            try:
                row,ev=execute_metric(out,run_id,metric,routes[metric['id']],dict(config,metric_index=i),cache,assessments.get(metric['id']))
            except Exception as e:
                raise RuntimeError(f"CORE_METRIC_{metric['id']}_INTERNAL_ERROR: {e}") from e
            results.append(row)
            if ev:evidence.append(ev)
        preflight['capabilities']=[dict(c,verified_success=any(receipt['outcome'] in {'SUCCESS_RAW','SUCCESS_VERIFIED'}
            for row in results if routes[row['metric_id']]['capability_id']==c['capability_id']
            for rel in row['execution_proof']['attempt_receipts']
            for receipt in [json.loads((out/rel).read_text())])) for c in preflight['capabilities']]
        atomic(out/'capability-preflight.json',preflight)
        bundle={'schema_version':'2.0','binding_contract_version':'1.0.0','target_url':url,'execution_run_id':run_id,'mode':'LIVE',
                'generated_at':now(),'evidence_catalog':evidence,'results':results}
        atomic(out/BUNDLE_NAME,bundle)
        status=validate_execution(root,out,bundle)
        atomic(out/'execution-run-summary.json',{'execution_run_id':run_id,'target_url':url,'mode':'LIVE',
            'registry_completeness':status['checked'],'execution_completeness':status['execution_completeness'],
            'completed_obligations':status['completed'],'score_admitted':status['score_admitted'],
            'state_counts':status['state_counts'],'does_not_prove':['customer release','scoring absent rubric']})
        print(f"{'PASS' if status['execution_completeness']=='PASS' else 'BLOCKED'}: planned=48 verified_closed={status['completed']}/48 admitted={status['score_admitted']} run_id={run_id} artifacts={out}")
        return 0 if status['execution_completeness']=='PASS' else 2
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
