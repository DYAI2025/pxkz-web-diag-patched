#!/usr/bin/env python3
"""Issue/verify digest-bound completion receipt; missing evidence fails customer readiness."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from core_execution_gate import validate_execution,sha
from core_active_measurement import semantic_digest

RECEIPT_FILE='execution-completeness-receipt.json'

def make_receipt(root:Path,run_dir:Path,bundle:dict,*,scored:Path|None=None)->dict:
    status=validate_execution(root,run_dir,bundle)
    if status['execution_completeness']=='PASS':
        from core_active_measurement import validate_bundle
        validate_bundle(root,bundle,run_dir=run_dir)
    preflight=run_dir/'capability-preflight.json'
    if not preflight.is_file():raise ValueError('CAPABILITY_PREFLIGHT_REQUIRED')
    pre=json.loads(preflight.read_text())
    registered=json.loads((root/'assets/capability-registry.json').read_text())
    expected_ids={c['id'] for c in registered['capabilities']}
    rows=pre.get('capabilities')
    if pre.get('target_url')!=bundle['target_url'] or not isinstance(rows,list) or len(rows)!=14 or {c.get('capability_id') for c in rows}!=expected_ids:
        raise ValueError('CAPABILITY_PREFLIGHT_SCOPE_OR_PARITY_FAIL')
    for row in rows:
        for art in row.get('evidence_files',[]):
            from validate_metric_attempt_receipts import confined
            path_art=confined(run_dir,art['path'])
            if sha(path_art)!=art['sha256']:raise ValueError('CAPABILITY_PREFLIGHT_ARTIFACT_DRIFT')
        if row.get('verified_success') is True:
            cap=row['capability_id']
            from validate_metric_execution_routes import load_checked
            by={r['metric_id']:r['capability_id'] for r in load_checked(root)['metrics']}
            receipts=[rel for r in bundle['results'] if by[r['metric_id']]==cap for rel in r['execution_proof']['attempt_receipts']]
            if not any(json.loads((run_dir/rel).read_text())['outcome'] in {'SUCCESS_RAW','SUCCESS_VERIFIED'} for rel in receipts):
                raise ValueError('CAPABILITY_FALSE_VERIFIED_SUCCESS')
    if scored is not None:
        if not scored.is_file():raise ValueError('SCORED_REPORT_MISSING')
        s=json.loads(scored.read_text())
        scores={m.get('id'):m for m in s.get('metrics',[]) if isinstance(m,dict)}
        if len(scores)!=48 or len(s.get('metrics',[]))!=48:
            raise ValueError('SCORED_REPORT_METRIC_PARITY_FAIL')
        for result in bundle['results']:
            m=scores.get(result['metric_id'])
            if m is None:raise ValueError('SCORED_METRIC_MISSING')
            admitted=result['execution_proof']['completion_state']=='VERIFIED_RESULT'
            if admitted:
                if m.get('measurement_class') not in {'measured','observed'} or m.get('status')!=result['product_status'] or m.get('value')!=result['value']:
                    raise ValueError('SCORED_RESULT_NOT_BOUND_TO_EXECUTED_VALUE')
            elif m.get('score') is not None or m.get('measurement_class') in {'measured','observed'}:
                raise ValueError('SCORE_ON_UNADMITTED_METRIC')
    path=run_dir/'core-execution-bundle.json'
    if not path.is_file():raise ValueError('CORE_BUNDLE_MISSING')
    canonical=json.loads(path.read_text())
    if canonical!=bundle:raise ValueError('BUNDLE_FILE_DIFFERS_FROM_VALIDATED_INPUT')
    # Coverage is computed from the same registered category/metric weights used by
    # canonical compute_score.py; the scorer, anchors and release thresholds remain untouched.
    registry=json.loads((root/'assets/measurement-registry.json').read_text())
    state_by={r['metric_id']:r['execution_proof']['completion_state'] for r in bundle['results']}
    category_coverage=[]
    for category,definition in registry['categories'].items():
        applicable=[x for x in registry['metrics'] if x['category']==category and state_by[x['id']]!='VERIFIED_NOT_APPLICABLE']
        den=sum(float(m['weight']) for m in applicable)
        num=sum(float(m['weight']) for m in applicable if state_by[m['id']]=='VERIFIED_RESULT')
        category_coverage.append((float(definition['weight']),num/den if den else 0.0))
    weighted_coverage_percent=round(sum(weight*coverage for weight,coverage in category_coverage) / 100.0 * 100.0,6)
    score_digest=sha(scored) if scored is not None and scored.is_file() else None
    return {'receipt_version':'1.0','execution_run_id':bundle['execution_run_id'],'target_url':bundle['target_url'],
        'mode':bundle['mode'],'registry_sha256':sha(root/'assets/measurement-registry.json'),
        'binding_sha256':sha(root/'assets/core-evidence-bindings.active.v1.json'),
        'route_catalog_sha256':sha(root/'assets/metric-execution-routes.v1.json'),
        'capability_preflight_sha256':sha(preflight),
        'bundle_sha256':sha(path),'execution_semantic_digest':semantic_digest(bundle),
        'scored_report_sha256':score_digest,'registry_completeness':48,'execution_completeness':status['execution_completeness'],
        'completed_obligations':status['completed'],'score_admitted':status['score_admitted'],
        'weighted_score_coverage':weighted_coverage_percent,'weighted_score_coverage_unit':'percent','customer_release_readiness':'PENDING_QA' if bundle['mode']=='LIVE' and status['execution_completeness']=='PASS' else 'BLOCKED',
        'status':'PASS' if status['execution_completeness']=='PASS' else 'FAIL', 'state_counts':status['state_counts'],
        'does_not_prove':['independent cryptographic origin beyond locally writable collector','customer QA','commercial outcome','semantic accuracy of human rubric']}


def validate_receipt(root:Path,run_dir:Path,receipt:dict,*,scored:Path|None=None,require_live:bool=True)->dict:
    bundle=json.loads((run_dir/'core-execution-bundle.json').read_text())
    expected=make_receipt(root,run_dir,bundle,scored=scored)
    for key,value in expected.items():
        if receipt.get(key)!=value:raise ValueError(f'COMPLETION_RECEIPT_STALE_OR_FORGED: {key}')
    if receipt['status']!='PASS':raise ValueError('EXECUTION_COMPLETENESS_FAIL')
    if require_live and receipt['mode']!='LIVE':raise ValueError('FIXTURE_REPLAY_NOT_CUSTOMER_RELEASE')
    if scored is not None and not receipt['scored_report_sha256']:
        raise ValueError('SCORED_REPORT_DIGEST_REQUIRED')
    return receipt


def main()->int:
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('run_dir');p.add_argument('--scored-report');p.add_argument('--check-only',action='store_true');p.add_argument('--allow-fixture',action='store_true');args=p.parse_args()
    root=Path(args.root).resolve();run=Path(args.run_dir).resolve()
    scored=Path(args.scored_report).resolve() if args.scored_report else None
    try:
        bundle=json.loads((run/'core-execution-bundle.json').read_text())
        f=run/RECEIPT_FILE
        if args.check_only:
            receipt=json.loads(f.read_text());validate_receipt(root,run,receipt,scored=scored,require_live=not args.allow_fixture)
        else:
            receipt=make_receipt(root,run,bundle,scored=scored)
            f.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
            if receipt['status']!='PASS':raise ValueError(f"EXECUTION_INCOMPLETE {receipt['completed_obligations']}/48")
        print(f"PASS: execution complete=48/48 score_admitted={receipt['score_admitted']} mode={receipt['mode']}")
        return 0
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
