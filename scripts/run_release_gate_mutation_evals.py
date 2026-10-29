#!/usr/bin/env python3
"""Prove that Website Diagnosis v1.3 release validation fails closed on peer drift."""
from __future__ import annotations
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from validate_release_gate import (CUSTOMER_REPORT_BLOCKED, PROOF_QA_PASS, PROOF_SEMANTIC_PASS, tree_digest, RELEASE_CASES, validate_font_gate,
                                   validate_reports, validate_skill_package_release)
from semantic_release_evidence import semantic_bundle_digest


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: run_release_gate_mutation_evals.py <skill-dir>", file=sys.stderr); return 1
    root=Path(argv[1]).resolve(); cp=root/'contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json'; c=json.loads(cp.read_text()); d=hashlib.sha256(cp.read_bytes()).hexdigest(); sd=semantic_bundle_digest(root); td=tree_digest(root)
    report={
      'release_scope':'website-diagnosis-package','release_gate':{'status':'PASS','allowed_to_package':True},
      'craftsmanship_gate':{'status':'PASS'},'anti_confabulation_gate':{'status':'PASS','blocked_claims':[]},
      'anti_sycophancy':{'score':0,'threshold':3},'bias_gate':{'status':'PASS'},'browser_gate':{'applicable':True,'status':'PASS','blockers':[]},
      'truth_discipline_gate':{'status':'PASS'},'batch_contract_gate':{'status':'PASS','default_version':'1.3.0','expected_fields':96,'custom_dynamic_variables':95,'contract_sha256':d},
      'batch_evals_gate':{'status':'PASS'},'core_regression_gate':{'status':'PASS'},'customer_semantic_gate':{'status':'PASS','policy_version':'1.0','semantic_bundle_sha256':sd,'artifact_digest':td},
      'cross_skill_dependency':{'status':'PASS','website_skill_side_status':'PASS','voice_architect_side_status':'PASS','shared_v1_3_sha256':d,'shared_contract_version':'1.3.0','website_fields':96,'voice_fields':96,'voice_custom_dynamic_variables':95,'actual_installed_consumer_validation':'PASS','voice_release_harness':'PASS'}
    }
    report['customer_report_release']={'status':'PASS','package_blocking':False}
    semantic={'status':'PASS','semantic_bundle_sha256':sd,'artifact_digest':td,'semantic_qa_validation':'PASS','visual_qa_validation':'PASS','inspection_method':'agent_vision','page_count':12,'release_mode':'customer','data_class':'REAL_AUDIT_INPUT','audit_input_sha256':'c'*64,'pdf_sha256':'d'*64}
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
    expect('semantic_evidence_build_digest_stale', lambda r,p,sem: sem.__setitem__('artifact_digest','0'*64))
    expect('semantic_gate_build_digest_stale', lambda r,p,sem: r['customer_semantic_gate'].__setitem__('artifact_digest','0'*64))
    # CUSTOMER_REPORT_RELEASE: a customer semantic PASS needs a real audit built in customer mode; blocked is a valid,
    # non-package-blocking state. A proof or example-data PASS must never read as a released customer report.
    expect('customer_pass_on_proof_mode', lambda r,p,sem: sem.__setitem__('release_mode','proof'))
    expect('customer_pass_on_example_data', lambda r,p,sem: sem.__setitem__('data_class','EXAMPLE_DATA'))
    expect('customer_release_status_invalid', lambda r,p,sem: r['customer_report_release'].__setitem__('status','READY'))
    expect('customer_release_missing', lambda r,p,sem: r.pop('customer_report_release'))
    # Review round 1 (a65c5b6): data_class alone is a self-declared label; bind a customer PASS to an audit input that is
    # no repository file, a PDF that is no proof, and a record without fixture provenance.
    fixture_sha=hashlib.sha256((root/'evals/fixtures/synthetic-report.json').read_bytes()).hexdigest()
    expect('customer_pass_relabelled_fixture_record', lambda r,p,sem: sem.__setitem__('fixture','evals/fixtures/synthetic-report.json'))
    expect('customer_pass_audit_input_is_repo_fixture', lambda r,p,sem: sem.__setitem__('audit_input_sha256',fixture_sha))
    expect('customer_pass_without_audit_input', lambda r,p,sem: sem.pop('audit_input_sha256'))
    expect('customer_pass_without_pdf', lambda r,p,sem: sem.pop('pdf_sha256'))
    cases.append(('customer_pass_pdf_is_a_proof', bool(validate_reports(root,report,paired,semantic,proof_pdfs={'d'*64})), []))
    blocked=lambda r,p,sem: (r['customer_report_release'].update({'status':CUSTOMER_REPORT_BLOCKED,'customer_release_ready':False}), r['customer_semantic_gate'].__setitem__('status','FAIL'), sem.update({'status':'FAIL','semantic_qa_validation':'FAIL','release_mode':'proof','data_class':'EXAMPLE_DATA'}))
    r0=copy.deepcopy(report); p0=copy.deepcopy(paired); s0=copy.deepcopy(semantic); blocked(r0,p0,s0)
    assert not validate_reports(root,r0,p0,s0), validate_reports(root,r0,p0,s0)  # positive control: blocked customer release
    expect('customer_blocked_but_package_blocking', lambda r,p,sem: (blocked(r,p,sem), r['customer_report_release'].__setitem__('package_blocking',True)))
    expect('customer_blocked_but_release_ready', lambda r,p,sem: (blocked(r,p,sem), r['customer_report_release'].__setitem__('customer_release_ready',True)))
    expect('customer_blocked_with_semantic_pass_variant', lambda r,p,sem: (blocked(r,p,sem), sem.__setitem__('status','PASS_WITH_ASSUMPTIONS')))
    expect('customer_blocked_with_gate_pass_claim', lambda r,p,sem: (blocked(r,p,sem), r['customer_semantic_gate'].__setitem__('status','PASS')))
    expect('customer_blocked_but_other_gate_ready', lambda r,p,sem: (blocked(r,p,sem), r.__setitem__('strict_customer_output_gate',{'status':'PASS','customer_release_ready':True})))
    expect('customer_blocked_with_gate_semantic_pass', lambda r,p,sem: (blocked(r,p,sem), r.__setitem__('proof_output_gate',{'status':'PASS','semantic_qa':'PASS'})))
    expect('customer_blocked_with_example_semantic_pass', lambda r,p,sem: (blocked(r,p,sem), sem.__setitem__('semantic_qa_validation','PASS')))
    # SKILL_PACKAGE_RELEASE: proofs prove function only; reviewed against the fixed checklist and bound to the live tree.
    pdf='a'*64
    import re
    release_cases=['proof-realistic',*sorted(RELEASE_CASES-{'proof-realistic'})]
    probes=re.findall(r'^\| ([A-E]\d) \|', (root/'docs/plans/2026-10-29-customer-pdf-qa-probe-checklist.md').read_text(encoding='utf-8'), re.M)
    qa={'status':PROOF_QA_PASS,'artifact_digest':td,'unadjudicated':[],'yardstick_sha256':hashlib.sha256((root/'docs/plans/2026-10-29-customer-pdf-qa-probe-checklist.md').read_bytes()).hexdigest(),
        'independent_review':{'rounds':[{'round':4,'fail':0,'probe_lines':{k:'PASS' for k in probes}}]},
        'cases':[{'case':c,'release_mode':'proof','pdf_sha256':pdf,'visual_qa':'PASS','deliverable_status':'CUSTOMER_RELEASE_BLOCKED'} for c in release_cases],
        'customer_mode_refusals':[{'case':c,'blocked':True,'pdf_written':False} for c in release_cases]}
    proof={'release_mode':'proof','customer_release_ready':False,'visual_qa':'PASS','proof_semantic_qa':PROOF_SEMANTIC_PASS,'semantic_qa':'FAIL','pdf_sha256':pdf}
    pkg={'skill_package_release':{'status':'PASS','artifact_digest':td}}
    assert not validate_skill_package_release(root,pkg,qa,{'realistic':proof}), validate_skill_package_release(root,pkg,qa,{'realistic':proof})
    def expect_pkg(name, mutate):
        r=copy.deepcopy(pkg); q=copy.deepcopy(qa); pr={'realistic':copy.deepcopy(proof)}; mutate(r,q,pr); errs=validate_skill_package_release(root,r,q,pr); cases.append((name,bool(errs),errs))
    expect_pkg('package_status_not_pass', lambda r,q,pr: r['skill_package_release'].__setitem__('status','BLOCKED'))
    expect_pkg('package_digest_stale', lambda r,q,pr: r['skill_package_release'].__setitem__('artifact_digest','0'*64))
    expect_pkg('proof_qa_not_pass', lambda r,q,pr: q.__setitem__('status','PENDING'))
    expect_pkg('proof_qa_digest_stale', lambda r,q,pr: q.__setitem__('artifact_digest','0'*64))
    expect_pkg('proof_qa_unadjudicated', lambda r,q,pr: q.__setitem__('unadjudicated',['B2 on case-a']))
    expect_pkg('proof_qa_review_failed', lambda r,q,pr: q['independent_review']['rounds'][-1].__setitem__('fail',1))
    expect_pkg('proof_qa_yardstick_changed', lambda r,q,pr: q.__setitem__('yardstick_sha256','0'*64))
    expect_pkg('proof_case_visual_not_pass', lambda r,q,pr: q['cases'][0].__setitem__('visual_qa','PENDING'))
    expect_pkg('proof_case_customer_ready', lambda r,q,pr: q['cases'][0].__setitem__('deliverable_status','CUSTOMER_RELEASE_READY'))
    expect_pkg('proof_case_customer_mode', lambda r,q,pr: q['cases'][0].__setitem__('release_mode','customer'))
    expect_pkg('customer_mode_wrote_pdf', lambda r,q,pr: q['customer_mode_refusals'][0].__setitem__('pdf_written',True))
    expect_pkg('proof_claims_customer_ready', lambda r,q,pr: pr['realistic'].__setitem__('customer_release_ready',True))
    expect_pkg('proof_claims_customer_semantic_pass', lambda r,q,pr: pr['realistic'].__setitem__('semantic_qa','PASS'))
    expect_pkg('proof_semantic_not_checklist_pass', lambda r,q,pr: pr['realistic'].__setitem__('proof_semantic_qa','FAIL'))
    expect_pkg('proof_pdf_not_reviewed', lambda r,q,pr: pr['realistic'].__setitem__('pdf_sha256','b'*64))
    expect_pkg('proof_qa_review_fail_not_int', lambda r,q,pr: q['independent_review']['rounds'][-1].__setitem__('fail',False))
    expect_pkg('proof_qa_review_latest_round_failed', lambda r,q,pr: q['independent_review']['rounds'].insert(0,{'round':5,'fail':3,'confirmed':3,'probe_lines':{}}))
    expect_pkg('proof_qa_probe_not_pass', lambda r,q,pr: q['independent_review']['rounds'][-1]['probe_lines'].__setitem__('B2','AMBIGUOUS'))
    expect_pkg('proof_qa_probe_missing', lambda r,q,pr: q['independent_review']['rounds'][-1]['probe_lines'].pop('E2'))
    expect_pkg('proof_case_visual_pass_with_rc1', lambda r,q,pr: q['cases'][0].__setitem__('visual_qa','PASS (validate_pdf_visual_qa rc 1)'))
    expect_pkg('proof_case_without_refusal', lambda r,q,pr: q['customer_mode_refusals'][0].__setitem__('case','other-case'))
    expect_pkg('proof_case_entry_not_object', lambda r,q,pr: q['cases'].append('pdf written'))
    expect_pkg('proof_without_pdf_sha', lambda r,q,pr: (pr['realistic'].pop('pdf_sha256'), q['cases'].append({'case':'x','release_mode':'proof','visual_qa':'PASS','deliverable_status':'CUSTOMER_RELEASE_BLOCKED'}), q['customer_mode_refusals'].append({'case':'x','blocked':True,'pdf_written':False})))
    expect_pkg('proof_qa_case_set_trimmed', lambda r,q,pr: q.__setitem__('cases',q['cases'][:1]))
    expect_pkg('proof_built_in_customer_mode', lambda r,q,pr: pr['realistic'].__setitem__('release_mode','customer'))
    manifest=root/'assets/fonts/font-manifest.json'; md=hashlib.sha256(manifest.read_bytes()).hexdigest()
    font_report={'strict_customer_output_gate':{'status':'PASS','customer_release_ready':False},'brand_rendering_gate':{'font_binary_policy':'PACKAGE_BUNDLED_MANIFEST_PINNED','strict_customer_mode_fail_closed':True,'font_manifest_sha256':md}}
    fonts={'exact':{'display':True,'data':True},'package_policy':'PACKAGE_BUNDLED_MANIFEST_PINNED','package_fonts':{'manifest_sha256':md}}
    assert not validate_font_gate(root,font_report,fonts), validate_font_gate(root,font_report,fonts)
    def expect_font(name, mutate):
        r=copy.deepcopy(font_report); f=copy.deepcopy(fonts); mutate(r,f); errs=validate_font_gate(root,r,f); cases.append((name,bool(errs),errs))
    expect_font('font_policy_not_bundled_legacy', lambda r,f: r['brand_rendering_gate'].__setitem__('font_binary_policy','NOT_BUNDLED'))
    expect_font('font_exact_but_strict_blocked', lambda r,f: r['strict_customer_output_gate'].__setitem__('status','BLOCKED_EXTERNAL_FONT'))
    expect_font('font_missing_but_strict_pass', lambda r,f: f['exact'].__setitem__('display',False))
    expect_font('font_missing_but_release_ready', lambda r,f: (f['exact'].__setitem__('data',False), r['strict_customer_output_gate'].update({'status':'BLOCKED_EXTERNAL_FONT','customer_release_ready':True})))
    expect_font('font_strict_not_fail_closed', lambda r,f: r['brand_rendering_gate'].__setitem__('strict_customer_mode_fail_closed',False))
    expect_font('font_capability_stale_manifest', lambda r,f: f['package_fonts'].__setitem__('manifest_sha256','0'*64))
    expect_font('font_gate_stale_manifest', lambda r,f: r['brand_rendering_gate'].__setitem__('font_manifest_sha256','0'*64))
    expect_font('font_capability_legacy_policy', lambda r,f: f.__setitem__('package_policy','FONT_BINARIES_MUST_NOT_BE_BUNDLED'))
    with tempfile.TemporaryDirectory(prefix='pxk-font-gate-') as tmp:
        rogue_root=Path(tmp)/'skill'
        shutil.copytree(root/'scripts',rogue_root/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(root/'assets/fonts',rogue_root/'assets/fonts')
        assert not validate_font_gate(rogue_root,font_report,fonts), validate_font_gate(rogue_root,font_report,fonts)
        shutil.copyfile(root/'assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf',rogue_root/'scripts/rogue.bin')
        errs=validate_font_gate(rogue_root,font_report,fonts); cases.append(('font_live_allowlist_rogue_font',any('allowlist live check failed' in e for e in errs),errs))
    failed=[name for name,blocked,_ in cases if not blocked]
    if failed:
        print('FAIL: mutations not blocked: '+', '.join(failed),file=sys.stderr); return 1
    print(f'PASS: release-gate mutation evals ({len(cases)} fail-closed cases)')
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
