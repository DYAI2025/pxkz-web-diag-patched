#!/usr/bin/env python3
"""Customer release chain: validate LIVE run, scored-report digest, and copied raw collector evidence."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from validate_audit_execution_completeness import validate_receipt
from validate_metric_attempt_receipts import confined
from core_execution_gate import sha

def normalized_url(url:str)->str:
    p=urlsplit(url)
    return (p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',p.query)

def validate_customer_run(root:Path,run_dir:Path,scored:Path,require_live:bool=True)->dict:
    receipt=json.loads((run_dir/'execution-completeness-receipt.json').read_text())
    validate_receipt(root,run_dir,receipt,scored=scored,require_live=require_live)
    report=json.loads(scored.read_text())
    url=(report.get('meta') or {}).get('audited_url')
    if not isinstance(url,str) or normalized_url(url)!=normalized_url(receipt['target_url']):
        raise ValueError('CUSTOMER_AUDIT_TARGET_MISMATCH')
    if receipt.get('execution_completeness')!='PASS' or receipt.get('completed_obligations')!=48:
        raise ValueError('CUSTOMER_EXECUTION_COMPLETENESS_REQUIRED')
    if receipt.get('customer_release_readiness')!='PENDING_QA':
        raise ValueError('CUSTOMER_RELEASE_NOT_ELIGIBLE')
    return receipt

def copy_proof(root:Path,source_dir:Path,out_dir:Path,scored:Path)->dict:
    receipt=validate_customer_run(root,source_dir,scored,require_live=True)
    bundle=json.loads((source_dir/'core-execution-bundle.json').read_text())
    files={'execution-completeness-receipt.json','core-execution-bundle.json','capability-preflight.json'}
    for row in bundle['results']:
        for rel in row['execution_proof']['attempt_receipts']:
            item=json.loads(confined(source_dir,rel).read_text())
            files.add(rel)
            for art in item['artifacts']:
                files.add(art['path'])
    proof=out_dir/'execution-proof'
    for rel in sorted(files):
        src=confined(source_dir,rel)
        dst=proof/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
    reread=validate_customer_run(root,proof,scored,require_live=True)
    if reread!=receipt:raise ValueError('COPIED_PROOF_READBACK_DRIFT')
    return {'proof_path':'execution-proof','execution_run_id':receipt['execution_run_id'],
            'target_url':receipt['target_url'],'bundle_sha256':receipt['bundle_sha256'],
            'scored_report_sha256':receipt['scored_report_sha256'],
            'receipt_sha256':sha(proof/'execution-completeness-receipt.json'),
            'registry_sha256':receipt['registry_sha256'],'binding_sha256':receipt['binding_sha256'],
            'route_catalog_sha256':receipt['route_catalog_sha256'],'mode':'LIVE','verified_receipts':sum(len(x['execution_proof']['attempt_receipts']) for x in bundle['results'])}

def validate_manifest_proof(root:Path,out_dir:Path,manifest:dict)->dict:
    binding=manifest.get('execution_proof')
    if not isinstance(binding,dict) or binding.get('proof_path')!='execution-proof':
        raise ValueError('CUSTOMER_EXECUTION_PROOF_MISSING')
    scored=out_dir/'diagnosis-report.json'
    run_dir=out_dir/'execution-proof'
    r=validate_customer_run(root,run_dir,scored,require_live=True)
    if any(binding.get(key)!=value for key,value in {
        'execution_run_id':r['execution_run_id'],'target_url':r['target_url'],
        'bundle_sha256':r['bundle_sha256'],'scored_report_sha256':r['scored_report_sha256'],
        'registry_sha256':r['registry_sha256'],'binding_sha256':r['binding_sha256'],
        'route_catalog_sha256':r['route_catalog_sha256'],
        'receipt_sha256':sha(run_dir/'execution-completeness-receipt.json'),'mode':'LIVE'}.items()):
        raise ValueError('CUSTOMER_EXECUTION_PROOF_DIGEST_DRIFT')
    if manifest.get('source_report_sha256')!=sha(scored):
        raise ValueError('CUSTOMER_SOURCE_SHA_DRIFT')
    return r
