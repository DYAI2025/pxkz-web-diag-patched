#!/usr/bin/env python3
"""Prove that Website Diagnosis v1.3 release validation fails closed on peer drift."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from pathlib import Path
from validate_release_gate import validate_reports
from semantic_release_evidence import semantic_bundle_digest


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_release_gate_mutation_evals.py <skill-dir>", file=sys.stderr); return 1
    root=Path(argv[1]).resolve(); cp=root/'contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json'; c=json.loads(cp.read_text()); d=hashlib.sha256(cp.read_bytes()).hexdigest(); sd=semantic_bundle_digest(root)
    report={
      'release_scope':'website-diagnosis-package','release_gate':{'status':'PASS','allowed_to_package':True},
      'craftsmanship_gate':{'status':'PASS'},'anti_confabulation_gate':{'status':'PASS','blocked_claims':[]},
      'anti_sycophancy':{'score':0,'threshold':3},'bias_gate':{'status':'PASS'},'browser_gate':{'applicable':True,'status':'PASS','blockers':[]},
      'truth_discipline_gate':{'status':'PASS'},'batch_contract_gate':{'status':'PASS','default_version':'1.3.0','expected_fields':96,'custom_dynamic_variables':95,'contract_sha256':d},
      'batch_evals_gate':{'status':'PASS'},'core_regression_gate':{'status':'PASS'},'customer_semantic_gate':{'status':'PASS','policy_version':'1.0','semantic_bundle_sha256':sd},
      'cross_skill_dependency':{'status':'PASS','website_skill_side_status':'PASS','voice_architect_side_status':'PASS','shared_v1_3_sha256':d,'shared_contract_version':'1.3.0','website_fields':96,'voice_fields':96,'voice_custom_dynamic_variables':95,'actual_installed_consumer_validation':'PASS','voice_release_harness':'PASS'}
    }
    semantic={'status':'PASS','semantic_bundle_sha256':sd,'semantic_qa_validation':'PASS','visual_qa_validation':'PASS','inspection_method':'agent_vision','page_count':12}
    paired={'status':'PASS','contract':{'version':'1.3.0','sha256':d,'field_count':96,'custom_dynamic_variable_count':95},'website_skill_side_status':'PASS','voice_architect_side_status':'PASS','voice_release_harness':{'status':'PASS'},'provider_neutral_packet_e2e':'PASS','truth_attack_e2e':'PASS','consumer_skill_dir':'/actual/consumer'}
    cases=[]
    def expect(name, mutate):
        r=copy.deepcopy(report); p=copy.deepcopy(paired); sem=copy.deepcopy(semantic); mutate(r,p,sem); errs=validate_reports(root,r,p,sem); cases.append((name,bool(errs),errs))
    assert not validate_reports(root,report,paired,semantic), validate_reports(root,report,paired,semantic)
    expect('voice_side_fail', lambda r,p,sem: r['cross_skill_dependency'].__setitem__('voice_architect_side_status','FAIL'))
    expect('shared_digest_mismatch', lambda r,p,sem: r['cross_skill_dependency'].__setitem__('shared_v1_3_sha256','0'*64))
    expect('version_mismatch', lambda r,p,sem: r['cross_skill_dependency'].__setitem__('shared_contract_version','1.2.0'))
    expect('voice_field_count_mismatch', lambda r,p,sem: r['cross_skill_dependency'].__setitem__('voice_fields',82))
    expect('paired_status_fail', lambda r,p,sem: p.__setitem__('status','FAIL'))
    expect('paired_digest_mismatch', lambda r,p,sem: p['contract'].__setitem__('sha256','f'*64))
    expect('voice_harness_fail', lambda r,p,sem: p['voice_release_harness'].__setitem__('status','FAIL'))
    expect('truth_e2e_fail', lambda r,p,sem: p.__setitem__('truth_attack_e2e','FAIL'))
    expect('semantic_gate_fail', lambda r,p,sem: r['customer_semantic_gate'].__setitem__('status','FAIL'))
    expect('semantic_bundle_mismatch', lambda r,p,sem: r['customer_semantic_gate'].__setitem__('semantic_bundle_sha256','0'*64))
    expect('semantic_evidence_fail', lambda r,p,sem: sem.__setitem__('status','FAIL'))
    failed=[name for name,blocked,_ in cases if not blocked]
    if failed:
        print('FAIL: mutations not blocked: '+', '.join(failed),file=sys.stderr); return 1
    print(f'PASS: release-gate mutation evals ({len(cases)} fail-closed cases)')
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
