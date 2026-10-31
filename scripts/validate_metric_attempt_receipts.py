#!/usr/bin/env python3
"""Verify actual on-disk receipt files and raw artifacts, never author tool evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import jsonschema
from validate_metric_execution_routes import load_checked


def digest(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def confined(root: Path, relative: str) -> Path:
    if not isinstance(relative,str) or not relative or '\\' in relative or '\x00' in relative:
        raise ValueError('INVALID_RELATIVE_PATH')
    candidate=Path(relative)
    if candidate.is_absolute() or any(x in {'.','..'} for x in candidate.parts):
        raise ValueError('PATH_TRAVERSAL_BLOCKED')
    full=root.joinpath(candidate)
    cur=root
    for part in candidate.parts:
        cur=cur/part
        if cur.is_symlink(): raise ValueError('SYMLINK_BLOCKED')
    if root.is_symlink() or not full.is_file() or not full.resolve().is_relative_to(root.resolve()):
        raise ValueError('ARTIFACT_MISSING_OR_OUTSIDE_RUN')
    return full


def _time(s:str):
    try:return datetime.fromisoformat(s.replace('Z','+00:00'))
    except Exception as e:raise ValueError('INVALID_RECEIPT_TIMESTAMP') from e


def validate_receipts(root:Path, run_dir:Path, bundle:dict, *, strict:bool=True)->dict[str,list[dict]]:
    catalog=load_checked(root)
    routes={r['metric_id']:r for r in catalog['metrics']}
    schema=json.loads((root/'schemas/metric-attempt-receipt.v1.schema.json').read_text())
    validator=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
    if not run_dir.is_dir():raise ValueError('RUN_DIRECTORY_MISSING')
    if (run_dir/'evidence').is_symlink():raise ValueError('SYMLINK_BLOCKED')
    receipts_by_id={}
    seen=set()
    for metric in bundle['results']:
        mid=metric['metric_id']
        proof=metric.get('execution_proof')
        if proof is None:
            if strict:raise ValueError(f'{mid}: LIVE_PROOF_REQUIRED')
            continue
        refs=proof.get('attempt_receipts')
        if not isinstance(refs,list) or len(refs)>4 or len(refs)!=len(set(refs)):
            raise ValueError(f'{mid}: INVALID_ATTEMPT_RECEIPT_LIST')
        attempts=[]
        for rel in refs:
            rp=confined(run_dir,rel)
            if not rp.name.endswith('.json') or not rel.startswith('evidence/receipts/'):
                raise ValueError(f'{mid}: INVALID_RECEIPT_LOCATION')
            if rel in seen:raise ValueError(f'{mid}: CROSS_METRIC_RECEIPT_REUSE')
            seen.add(rel)
            receipt=json.loads(rp.read_text(encoding='utf-8'))
            errors=list(validator.iter_errors(receipt))
            if errors:raise ValueError(f'{mid}: RECEIPT_SCHEMA_FAIL {errors[0].message}')
            if receipt['metric_id']!=mid or receipt['execution_run_id']!=bundle['execution_run_id']:
                raise ValueError(f'{mid}: CROSS_RUN_OR_METRIC_REFERENCE')
            if receipt['target_url']!=bundle['target_url']:
                raise ValueError(f'{mid}: RECEIPT_TARGET_MISMATCH')
            conf={c['route_id']:c for c in [routes[mid]['primary'],*routes[mid]['alternatives']]}
            route=conf.get(receipt['route_id'])
            if not route:raise ValueError(f'{mid}: UNAUTHORIZED_RECEIPT_ROUTE')
            for key in ('method_id','method_version','source_family','measurement_class','adapter'):
                if receipt[key]!=route[key]:raise ValueError(f'{mid}: RECEIPT_{key.upper()}_MISMATCH')
            if _time(receipt['finished_at'])<_time(receipt['started_at']):
                raise ValueError(f'{mid}: RECEIPT_NEGATIVE_DURATION')
            if receipt['tool']['name'] in {'agent','model','llm','none','unknown'}:
                raise ValueError(f'{mid}: MODEL_TEXT_IS_NOT_EXECUTOR')
            kinds=set()
            for artifact in receipt['artifacts']:
                path=confined(run_dir,artifact['path'])
                if not artifact['path'].startswith('evidence/raw/'):
                    raise ValueError(f'{mid}: RAW_ARTIFACT_LOCATION_INVALID')
                if path.stat().st_size!=artifact['bytes'] or digest(path)!=artifact['sha256']:
                    raise ValueError(f'{mid}: RAW_ARTIFACT_DIGEST_OR_SIZE_FAIL')
                kinds.add(artifact['kind'])
                if artifact['kind'] in {'http_response','provider_response'}:
                    try:response=json.loads(path.read_text())
                    except Exception as e:raise ValueError(f'{mid}: RESPONSE_NOT_JSON') from e
                    if response.get('observed_url')!=receipt['observed_url'] or response.get('requested_url')!=receipt['target_url']:
                        raise ValueError(f'{mid}: RESPONSE_URL_PROVENANCE_FAIL')
            outcome=receipt['outcome']
            if route['implementation_status'] in {'MISSING_CORE_ADAPTER','MISSING_MACHINE_COLLECTOR','MISSING_AXE_OR_BRIDGE','MISSING_METRIC_SPECIFIC_EVALUATOR','EXISTING_NONCORE_ONLY','AUTH_REQUIRED_NONCORE_ONLY'} and outcome!='IMPLEMENTATION_GAP' and not (outcome=='POLICY_BLOCKED' and route['permission']=='owner_authorized'):
                raise ValueError(f'{mid}: UNIMPLEMENTED_ROUTE_CANNOT_CLAIM_TOOL_EXECUTION')
            if outcome in {'SUCCESS_RAW','SUCCESS_VERIFIED','SOURCE_ABSENT'}:
                if route['adapter']=='PUBLIC_BROWSER' and not {'dom','viewport'}<=kinds:
                    raise ValueError(f'{mid}: BROWSER_DOM_VIEWPORT_REQUIRED')
                if route['adapter']=='PUBLIC_BROWSER' and receipt['configuration'].get('visual_claim') and 'screenshot' not in kinds:
                    raise ValueError(f'{mid}: BROWSER_SCREENSHOT_REQUIRED')
                if route['adapter']=='PUBLIC_HTTP' and not ({'http_response','html'} & kinds):
                    raise ValueError(f'{mid}: HTTP_RESPONSE_PROOF_REQUIRED')
                if route['adapter'] in {'PUBLIC_CRUX','PAGESPEED_API','PUBLIC_SEARCH'} and 'provider_response' not in kinds:
                    raise ValueError(f'{mid}: PROVIDER_RESPONSE_PROOF_REQUIRED')
                if route['adapter']=='LIGHTHOUSE_CLI' and 'lab_json' not in kinds:
                    raise ValueError(f'{mid}: LIGHTHOUSE_LAB_PROOF_REQUIRED')
                if outcome=='SOURCE_ABSENT':
                    provider_entries=[a for a in receipt['artifacts'] if a['kind']=='provider_response']
                    if not provider_entries:
                        raise ValueError(f'{mid}: SOURCE_ABSENT_REQUIRES_PROVIDER_RESPONSE')
                    response=json.loads(confined(run_dir,provider_entries[0]['path']).read_text())
                    if response.get('status_code')!=404 or response.get('source_absence_marker')!='HTTP_404_FROM_CRUX_API':
                        raise ValueError(f'{mid}: SOURCE_ABSENCE_MARKER_NOT_VERIFIED')
            else:
                if 'tool_log' not in kinds:
                    raise ValueError(f'{mid}: FAILURE_OR_BLOCK_REQUIRES_TOOL_LOG')
            if outcome=='TOOL_FAILURE' and receipt['tool']['exit_code'] in (None,0):
                raise ValueError(f'{mid}: TOOL_FAILURE_REQUIRES_NONZERO_EXIT')
            if outcome=='POLICY_BLOCKED' and route['permission']!='owner_authorized':
                raise ValueError(f'{mid}: PUBLIC_PERMISSION_CANNOT_BE_POLICY_BLOCKED')
            if outcome=='IMPLEMENTATION_GAP' and route['implementation_status'] in {'IMPLEMENTED','CONDITIONAL_RUNTIME'}:
                raise ValueError(f'{mid}: FALSE_IMPLEMENTATION_GAP')
            attempts.append(receipt)
        receipts_by_id[mid]=attempts
    return receipts_by_id


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('root');ap.add_argument('run_dir');ap.add_argument('--bundle');args=ap.parse_args()
    root=Path(args.root).resolve();d=Path(args.run_dir).resolve()
    try:
        bundle=json.loads((Path(args.bundle) if args.bundle else d/'core-execution-bundle.json').read_text())
        by=validate_receipts(root,d,bundle,strict=bundle.get('mode')=='LIVE')
        print(f'PASS: verified_receipts={sum(map(len,by.values()))} metrics_with_proof={len(by)}')
        return 0
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
