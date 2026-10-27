#!/usr/bin/env python3
"""Deterministic local provider-identification compliance sidecar. No network access."""
from __future__ import annotations
import argparse, json
from pathlib import Path

DEFECTS={"ABSENT","INCOMPLETE","INCORRECT","CONTRADICTORY","UNVERIFIABLE","INACCESSIBLE","NOT_CONTINUOUSLY_AVAILABLE","UNTIMELY"}
ADMIT_MC={"measured","observed"}; ADMIT_E={"E1","E2","E3","E4"}
DIM_MAP={"operator_identity":("LEGAL-IMP-02","identity"),"geographic_address":("LEGAL-IMP-03","geographic_address"),"email":("LEGAL-IMP-04","contactability"),"phone":("LEGAL-IMP-04","contactability"),"legal_form_rep":("LEGAL-IMP-05","legal_form_rep"),"registry":("LEGAL-IMP-06","registry"),"regulatory_profession":("LEGAL-IMP-07","regulatory_profession"),"conditional_ids":("LEGAL-IMP-08","conditional_ids"),"accessibility":("LEGAL-IMP-09","accessibility")}

def _load_registry(root:Path): return json.loads((root/'assets/impressum-compliance-registry.v1.json').read_text())
def _band(points:int)->str:
    return 'LOW' if points<=9 else 'MEDIUM' if points<=24 else 'HIGH' if points<=49 else 'CRITICAL'
def _jurisdiction(ctx):
    est=ctx.get('operator_establishment') if isinstance(ctx.get('operator_establishment'),dict) else None
    if est and est.get('country') and est.get('confidence') in {'HIGH','CONFIRMED'} and est.get('evidence_grade') in {'E1','E2','E3','E4'}:
        return {'status':'CONFIRMED','country':str(est['country']).upper(),'basis':'operator_establishment'}
    if ctx.get('jurisdiction_conflict'): return {'status':'CONFLICT','country':None,'basis':'conflicting establishment evidence'}
    return {'status':'UNRESOLVED','country':None,'basis':'weak signals are non-confirmatory'}
def _applicability(key,ctx,jur):
    if jur['status']!='CONFIRMED': return 'UNKNOWN'
    if jur['country']!='DE': return 'UNKNOWN'
    flags=set(ctx.get('business_flags') or [])
    if 'personal_family_only' in flags: return 'NOT_APPLICABLE'
    if key=='phone': return 'APPLICABLE' if ctx.get('audience_scope') in {'B2C','MIXED'} and ctx.get('distance_contract_status')=='CONFIRMED' else 'NOT_APPLICABLE'
    if key=='legal_form_rep': return 'APPLICABLE' if str(ctx.get('legal_form','')).lower() in {'gmbh','ag','ug','kg','kgaa','gbr','ohg','e.v.','ev','juristic_person','legal_entity'} else 'NOT_APPLICABLE'
    if key=='registry': return 'APPLICABLE' if ctx.get('registry_status')=='CONFIRMED' else ('CONDITIONAL' if ctx.get('registry_status') in {None,'UNKNOWN','LIKELY'} else 'NOT_APPLICABLE')
    if key=='regulatory_profession': return 'APPLICABLE' if ctx.get('regulated_profession_status')=='CONFIRMED' else 'CONDITIONAL'
    if key=='conditional_ids': return 'APPLICABLE' if ctx.get('conditional_id_status')=='CONFIRMED' else 'CONDITIONAL'
    if 'service_provider' in flags or flags & {'regulated_profession','licensed_activity','financial_service','journalistic_editorial','audiovisual_media_service','online_marketplace'}: return 'APPLICABLE'
    return 'UNKNOWN'
def _admitted(app,obs):
    return app=='APPLICABLE' and obs.get('measurement_class') in ADMIT_MC and obs.get('evidence_grade') in ADMIT_E and obs.get('defect_supported') is True and not obs.get('unresolved_conflict')
def _state(app,obs):
    if app=='NOT_APPLICABLE': return 'NOT_APPLICABLE'
    status=obs.get('status','UNKNOWN')
    if app in {'UNKNOWN','LIKELY_APPLICABLE','CONDITIONAL'}: return 'POSSIBLE_LEGAL_REVIEW' if status in DEFECTS else 'NOT_ASSESSED'
    if obs.get('unresolved_conflict') or status=='CONTRADICTORY': return 'CONFLICT'
    if status in DEFECTS: return 'ASSESSED_DEFECT'
    if status=='PRESENT': return 'ASSESSED_NO_DEFECT'
    return 'NOT_ASSESSED'
def _severity(metric, defect, points, app):
    if app!='APPLICABLE': return 'review'
    if metric in {'LEGAL-IMP-02','LEGAL-IMP-03'} and defect in {'ABSENT','UNTIMELY'}: return 'critical'
    if points>=15: return 'high'
    return 'medium' if points>=10 else 'low'

def assess_case(context:dict, observations:dict, *, root:Path|None=None, discovery_scope:dict|None=None):
    root=root or Path(__file__).resolve().parents[1]
    reg=_load_registry(root); weights=reg['iles_dimensions']; jur=_jurisdiction(context)
    source_needed=[]; applicable_regimes=[]
    if jur['status']=='CONFIRMED' and jur['country']=='DE': applicable_regimes=['EU-ECOM-2000-31-ART5','DE-DDG-5']
    elif jur['status']=='CONFIRMED' and jur['country']!='DE': source_needed.append('SOURCE_NEEDED: COUNTRY_OR_SECTOR_ADAPTER:'+jur['country'])
    results=[]; dims={k:0 for k in weights}; dimension_claimed=set()
    discovery_complete=True if discovery_scope is None else bool(discovery_scope.get('complete'))
    for key,obs0 in observations.items():
        if not isinstance(obs0,dict): continue
        obs=dict(obs0); status=obs.get('status','UNKNOWN')
        if status=='ABSENT' and not discovery_complete:
            status='UNKNOWN'; obs['status']='UNKNOWN'; obs['defect_supported']=False
        if key=='timing':
            if status!='UNTIMELY': continue
            base=obs.get('base_dimension'); metric='LEGAL-IMP-11'; app='APPLICABLE' if context.get('audience_scope') in {'B2C','MIXED'} and context.get('distance_contract_status')=='CONFIRMED' and jur.get('country')=='DE' else 'CONDITIONAL'
            results.append({'metric_id':metric,'base_dimension':base,'applicability_status':app,'result_state':_state(app,obs),'defect_type':'UNTIMELY','iles_points':0,'severity':'high' if app=='APPLICABLE' else 'review','evidence_grade':obs.get('evidence_grade'),'measurement_class':obs.get('measurement_class')})
            continue
        if key not in DIM_MAP: continue
        metric,dim=DIM_MAP[key]; app=_applicability(key,context,jur)
        if key=='phone' and app!='APPLICABLE':
            continue
        state=_state(app,obs)
        defect=status if status in DEFECTS else None
        points=0
        if _admitted(app,obs) and defect and dim not in dimension_claimed:
            points=int(weights[dim]); dims[dim]=points; dimension_claimed.add(dim)
        result={'metric_id':metric,'dimension':dim,'applicability_status':app,'result_state':state,'defect_type':defect,'iles_points':points,'severity':_severity(metric,defect,points,app),'evidence_grade':obs.get('evidence_grade'),'measurement_class':obs.get('measurement_class')}
        if defect: results.append(result)
        if defect=='UNTIMELY':
            results.append({'metric_id':'LEGAL-IMP-11','base_dimension':dim,'applicability_status':app,'result_state':result['result_state'],'defect_type':'UNTIMELY','iles_points':0,'severity':result['severity'],'evidence_grade':obs.get('evidence_grade'),'measurement_class':obs.get('measurement_class')})
        if defect in {'INCORRECT','CONTRADICTORY'}:
            if defect=='INCORRECT' and not obs.get('authoritative_counterevidence'):
                result['result_state']='POSSIBLE_LEGAL_REVIEW'; result['iles_points']=0; dims[dim]=0; dimension_claimed.discard(dim)
            results.append({'metric_id':'LEGAL-IMP-10','base_dimension':dim,'applicability_status':app,'result_state':'CONFLICT' if defect=='CONTRADICTORY' else result['result_state'],'defect_type':defect,'iles_points':0,'severity':'review' if defect=='CONTRADICTORY' else result['severity'],'evidence_grade':obs.get('evidence_grade'),'measurement_class':obs.get('measurement_class')})
    # IMP-01 aggregate only when provider-id set is materially absent
    defect_ids={r['metric_id'] for r in results if r['result_state']=='ASSESSED_DEFECT'}
    if {'LEGAL-IMP-02','LEGAL-IMP-03','LEGAL-IMP-04','LEGAL-IMP-09'}.issubset(defect_ids):
        results.insert(0,{'metric_id':'LEGAL-IMP-01','applicability_status':'APPLICABLE','result_state':'ASSESSED_DEFECT','defect_type':'ABSENT','iles_points':0,'severity':'critical','evidence_grade':'E1','measurement_class':'observed'})
    points=sum(dims.values())
    identity_critical=any(r['metric_id'] in {'LEGAL-IMP-02','LEGAL-IMP-03'} and r['result_state']=='ASSESSED_DEFECT' and r['defect_type'] in {'ABSENT','UNTIMELY'} and r.get('evidence_grade') in ADMIT_E for r in results)
    aggregate_critical=any(r['metric_id']=='LEGAL-IMP-01' and r['result_state']=='ASSESSED_DEFECT' for r in results)
    iles_critical=bool(identity_critical or aggregate_critical)
    observed_opacity=any(r['metric_id'] in {'LEGAL-IMP-02','LEGAL-IMP-03'} and r.get('defect_type') in {'ABSENT','INACCESSIBLE'} and r.get('evidence_grade') in ADMIT_E for r in results)
    audit_priority_critical=jur['status'] in {'UNRESOLVED','CONFLICT'} and observed_opacity
    if audit_priority_critical:
        for r in results:
            r['applicability_status']='UNKNOWN'; r['iles_points']=0
            if r['result_state']!='CONFLICT': r['result_state']='POSSIBLE_LEGAL_REVIEW'
        dims={k:0 for k in dims}; points=0; iles_critical=False
    exposure={'jurisdiction':jur.get('country'),'applicable_rule':'DE-DDG-33' if jur.get('country')=='DE' else None,'administrative_exposure':'POSSIBLE' if defect_ids and jur.get('country')=='DE' else 'NOT_ASSESSED','civil_exposure':'NOT_ASSESSED','criminal_exposure':'NOT_ASSESSED','sector_regulatory_exposure':'NOT_ASSESSED','statutory_maximum_eur':50000 if defect_ids and jur.get('country')=='DE' else None,'expected_penalty':None,'source':'https://www.gesetze-im-internet.de/ddg/__33.html' if jur.get('country')=='DE' else None,'confidence':'HIGH' if jur.get('country')=='DE' else 'UNKNOWN'}
    return {'schema_version':'1.0','jurisdiction':jur,'business_context':{'flags':context.get('business_flags',[]),'audience_scope':context.get('audience_scope','UNKNOWN'),'distance_contract_status':context.get('distance_contract_status','UNKNOWN')},'applicable_regimes':applicable_regimes,'results':results,'iles':{'points':points,'band':_band(points),'dimensions':dims},'overrides':{'iles_critical_override':iles_critical,'audit_priority_critical':audit_priority_critical},'enforcement_exposure':exposure,'source_needed':source_needed,'limitations':['Internal prioritization model; not a legal certification.','GDPR/DSGVO is a separate compliance dimension.'],'pixelkiez_score_impact':'NONE_DIRECT'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('evidence_json'); ap.add_argument('output_json'); args=ap.parse_args()
    payload=json.loads(Path(args.evidence_json).read_text()); out=assess_case(payload.get('context',{}),payload.get('observations',{}),discovery_scope=payload.get('discovery_scope'))
    Path(args.output_json).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(f"PASS: wrote {args.output_json} ILES={out['iles']['points']}")
if __name__=='__main__': main()
