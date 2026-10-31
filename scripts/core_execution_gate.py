#!/usr/bin/env python3
"""Deterministic, receipt-backed 48-obligation execution gate. No scoring implementation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from validate_metric_execution_routes import load_checked
from validate_metric_attempt_receipts import validate_receipts

CLOSED={"VERIFIED_RESULT","VERIFIED_UNAVAILABLE","VERIFIED_NOT_APPLICABLE","VERIFIED_POLICY_BLOCKED","VERIFIED_SOURCE_ABSENT","VERIFIED_TOOL_FAILURE"}
OPEN={"PENDING","CAPABILITY_CHECKED","ATTEMPTED","NOT_ATTEMPTED","EVIDENCE_CONFLICT"}


def validate_execution(root:Path,run_dir:Path,bundle:dict)->dict:
    catalog=load_checked(root)
    route_by={x['metric_id']:x for x in catalog['metrics']}
    if bundle.get('mode')=='LIVE' and bundle.get('schema_version')!='2.0':
        raise ValueError('LIVE_V1_BUNDLE_REJECTED')
    if bundle.get('schema_version')!='2.0':
        raise ValueError('EXECUTION_COMPLETENESS_NEEDS_V2')
    registry=json.loads((root/'assets/measurement-registry.json').read_text(encoding='utf-8'))
    mids={x['id'] for x in registry['metrics']}
    rows=bundle.get('results')
    if not isinstance(rows,list) or len(rows)!=48 or {r.get('metric_id') for r in rows}!=mids:
        raise ValueError('EXACT_48_REQUIRED')
    if len({r['metric_id'] for r in rows})!=48:raise ValueError('DUPLICATE_RESULT_ID')
    receipt_by=validate_receipts(root,run_dir,bundle,strict=True)
    evidence_catalog=bundle.get('evidence_catalog',[])
    if not isinstance(evidence_catalog,list):raise ValueError('INVALID_EVIDENCE_CATALOG')
    ev_by={e.get('id'):e for e in evidence_catalog if isinstance(e,dict)}
    if len(ev_by)!=len(evidence_catalog):raise ValueError('DUPLICATE_OR_MALFORMED_EVIDENCE')
    report=[]
    for row in rows:
        mid=row['metric_id'];proof=row['execution_proof'];state=proof.get('completion_state')
        if state not in CLOSED|OPEN:raise ValueError(f'{mid}: UNKNOWN_EXECUTION_STATE')
        attempts=receipt_by.get(mid,[])
        outcome=[a['outcome'] for a in attempts]
        order=[r['route_id'] for r in [route_by[mid]['primary'],*route_by[mid]['alternatives']]]
        used=[a['route_id'] for a in attempts]
        if len(used)!=len(set(used)) or used!=[r for r in order if r in set(used)]:
            raise ValueError(f'{mid}: FALLBACK_METHOD_ORDER_OR_DUPLICATE')
        if len(attempts)>4:raise ValueError(f'{mid}: FALLBACK_LIMIT_EXCEEDED')
        assessment=proof.get('assessment')
        if state=='VERIFIED_RESULT':
            if row['execution_state'] not in {'MEASURED','OBSERVED'} or not any(s in {'SUCCESS_RAW','SUCCESS_VERIFIED'} for s in outcome):
                raise ValueError(f'{mid}: SCORE_WITHOUT_EXECUTED_SOURCE')
            if not isinstance(assessment,dict) or not str(assessment.get('rubric_observation') or '').strip() or not str(assessment.get('rubric_reason') or '').strip():
                raise ValueError(f'{mid}: SITE_SPECIFIC_RUBRIC_REQUIRED')
            if assessment.get('product_status')!=row.get('product_status') or assessment.get('value')!=row.get('value'):
                raise ValueError(f'{mid}: RUBRIC_VALUE_STATUS_MISMATCH')
            if not row['evidence_refs']:raise ValueError(f'{mid}: SCORE_EVIDENCE_REF_REQUIRED')
            # Admission must bind each score evidence row to a *successful* inspected
            # method's byte-verified raw artifact, never a freestanding evidence note.
            verified_raw={(art['path'],art['sha256'],a['source_family'])
                          for a in attempts if a['outcome'] in {'SUCCESS_RAW','SUCCESS_VERIFIED'}
                          for art in a['artifacts'] if art['kind']!='tool_log'}
            for ref in row['evidence_refs']:
                evidence=ev_by.get(ref)
                if not isinstance(evidence,dict) or (
                    evidence.get('reference'),evidence.get('digest'),evidence.get('source_family')) not in verified_raw:
                    raise ValueError(f'{mid}: SCORE_EVIDENCE_NOT_BOUND_TO_RAW_COLLECTOR_BYTES')
                if evidence.get('target_url')!=bundle['target_url'] or evidence.get('status') not in {'OBSERVED','MEASURED'}:
                    raise ValueError(f'{mid}: SCORE_EVIDENCE_TARGET_OR_STATUS_DRIFT')
        elif state=='VERIFIED_POLICY_BLOCKED':
            if row['execution_state'] in {'MEASURED','OBSERVED'} or not outcome or outcome[-1]!='POLICY_BLOCKED':
                raise ValueError(f'{mid}: INVALID_POLICY_BLOCK')
            if route_by[mid]['permission_boundary'] not in {'owner_authorized','user_authorized_private'}:
                raise ValueError(f'{mid}: PUBLIC_METRIC_POLICY_BLOCK_FORBIDDEN')
        elif state=='VERIFIED_SOURCE_ABSENT':
            if row['execution_state'] in {'MEASURED','OBSERVED'} or not outcome or outcome[-1]!='SOURCE_ABSENT':
                raise ValueError(f'{mid}: SOURCE_ABSENCE_NOT_VERIFIED')
            if not any(a['adapter'] in {'PUBLIC_CRUX','OWNER_EXPORT','PUBLIC_SEARCH'} for a in attempts):
                raise ValueError(f'{mid}: SOURCE_ABSENT_NEEDS_AUTHORITATIVE_SOURCE')
        elif state=='VERIFIED_TOOL_FAILURE':
            if row['execution_state'] in {'MEASURED','OBSERVED'} or 'TOOL_FAILURE' not in outcome or any(s.startswith('SUCCESS') for s in outcome):
                raise ValueError(f'{mid}: TOOL_FAILURE_WITHOUT_FAILED_EXECUTION')
        elif state=='VERIFIED_UNAVAILABLE':
            if row['execution_state'] in {'MEASURED','OBSERVED'} or not outcome or any(x not in {'CAPABILITY_UNAVAILABLE'} for x in outcome):
                raise ValueError(f'{mid}: UNAVAILABLE_NOT_SUPPORTED_BY_CAPABILITY_PROOFS')
        elif state=='VERIFIED_NOT_APPLICABLE':
            if not route_by[mid]['not_applicable_rule']:
                raise ValueError(f'{mid}: NO_VERIFIED_APPLICABILITY_RULE')
        else:
            if row['execution_state'] in {'MEASURED','OBSERVED'}:
                raise ValueError(f'{mid}: OPEN_STATE_WITH_SCORE')
        if state in CLOSED and state!='VERIFIED_RESULT' and row.get('product_status') is not None:
            raise ValueError(f'{mid}: NONSCORE_VALUE_LEAK')
        if state in CLOSED and not attempts:raise ValueError(f'{mid}: UNATTEMPTED_CANNOT_CLOSE')
        slots=proof.get('fallback_slots_unavailable')
        if slots!=route_by[mid]['unavailable_fallback_slots']:
            raise ValueError(f'{mid}: FALLBACK_SLOT_ACCOUNTING_MISMATCH')
        evaluation=proof.get('fallback_evaluations')
        if not isinstance(evaluation,list) or len(evaluation)!=len(order)-len(used):
            raise ValueError(f'{mid}: FALLBACK_ACCOUNTING_MISSING')
        skipped={e.get('route_id') for e in evaluation if isinstance(e,dict)}
        if skipped!=set(order)-set(used):raise ValueError(f'{mid}: FALLBACK_ACCOUNTING_ROUTE_MISMATCH')
        if any(not str(e.get('reason') or '').strip() for e in evaluation):
            raise ValueError(f'{mid}: FALLBACK_REASON_MISSING')
        if state in {'VERIFIED_TOOL_FAILURE','VERIFIED_UNAVAILABLE','VERIFIED_SOURCE_ABSENT'}:
            if any(e['reason']=='IMPLEMENTATION_GAP' for e in evaluation) or any(x=='IMPLEMENTATION_GAP' for x in outcome):
                raise ValueError(f'{mid}: IMPLEMENTATION_GAP_CANNOT_CLOSE_AS_EXCEPTION')
            if any(e.get('reason') in {'UNREVIEWED','UNKNOWN','MISSING'} for e in evaluation):
                raise ValueError(f'{mid}: UNSUPPORTED_FALLBACK_SKIP')
        if state=='VERIFIED_RESULT' and assessment:
            if any(x['measurement_class']=='lab' for x in attempts) and route_by[mid]['primary']['measurement_class']=='field':
                raise ValueError(f'{mid}: LAB_NOT_FIELD')
        report.append({'metric_id':mid,'completion_state':state,'score_admitted':state=='VERIFIED_RESULT','attempts':len(attempts),
                      'actual_methods':[a['method_id'] for a in attempts]})
    counts={s:sum(r['completion_state']==s for r in report) for s in sorted(CLOSED|OPEN)}
    completed=sum(x['completion_state'] in CLOSED for x in report)
    score=sum(x['score_admitted'] for x in report)
    return {'checked':48,'completed':completed,'score_admitted':score,'execution_completeness':'PASS' if completed==48 else 'FAIL','state_counts':counts,'metrics':report}


def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
