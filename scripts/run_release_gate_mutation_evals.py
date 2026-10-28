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
from validate_release_gate import tree_digest, validate_font_gate, validate_reports
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
    semantic={'status':'PASS','semantic_bundle_sha256':sd,'artifact_digest':td,'semantic_qa_validation':'PASS','visual_qa_validation':'PASS','inspection_method':'agent_vision','page_count':12}
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
