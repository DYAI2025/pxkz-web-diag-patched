"""Patch A deterministic fake-input falsification; no tests claim real remote tool access."""
from __future__ import annotations
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from core_active_measurement import ContractError,validate_bundle
from core_capture import google_capture
from core_execution_gate import validate_execution
from run_48_core_metrics import execute_metric
from validate_metric_attempt_receipts import validate_receipts
from validate_metric_execution_routes import load_checked
from validate_audit_execution_completeness import make_receipt,validate_receipt

class ExecutionPatchATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='pxk48a-test-')
        cls.sample_dir=Path(cls.temp.name)/'sample'
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/run_48_core_metrics.py'), '--offline',
            '--target','https://example.org/','--output',str(cls.sample_dir)],capture_output=True,text=True,timeout=60)
        if proc.returncode!=2:raise RuntimeError(f'offline fixture failed rc={proc.returncode} {proc.stdout} {proc.stderr}')
        cls.bundle=json.loads((cls.sample_dir/'core-execution-bundle.json').read_text())
        cls.routes={r['metric_id']:r for r in load_checked(ROOT)['metrics']}
        cls.registry={r['id']:r for r in json.loads((ROOT/'assets/measurement-registry.json').read_text())['metrics']}
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def clone(self):
        d=Path(self.temp.name)/('copy-'+os.urandom(5).hex())
        shutil.copytree(self.sample_dir,d)
        return d,json.loads((d/'core-execution-bundle.json').read_text())
    def test_T01_live_v1_is_rejected(self):
        b=json.loads((ROOT/'evals/fixtures/full-48-core-execution.json').read_text())
        b['mode']='LIVE'
        with self.assertRaises(ContractError):validate_bundle(ROOT,b)
    def test_T02_shape_36_unavailable_has_no_proof(self):
        b=json.loads((ROOT/'evals/fixtures/full-48-core-execution.json').read_text())
        b['mode']='LIVE'
        # Synthetic 12 measured / 36 unassessed failure shape, NOT historical ZIP replay.
        for r in b['results'][12:]:
            r['execution_state']='UNAVAILABLE'
            r['reason_codes']=['EVIDENCE_UNAVAILABLE']
            r['value']=None;r['product_status']=None;r['evidence_refs']=[];r['evidence_grade']='E8'
        self.assertEqual(sum(r['execution_state']=='UNAVAILABLE' for r in b['results']),36)
        with self.assertRaises(ContractError):validate_bundle(ROOT,b)
    def test_T03_not_attempted_cannot_close_by_reason(self):
        d,b=self.clone();r=b['results'][0]
        r['execution_proof']['completion_state']='NOT_ATTEMPTED';r['execution_state']='UNAVAILABLE';r['reason_codes']=['EVIDENCE_UNAVAILABLE']
        result=validate_execution(ROOT,d,b)
        self.assertEqual(result['execution_completeness'],'FAIL')
    def test_T04_public_without_attempt_is_not_done(self):
        d,b=self.clone();r=b['results'][0];r['execution_proof']['attempt_receipts']=[]
        r['execution_proof']['completion_state']='VERIFIED_UNAVAILABLE';r['execution_state']='UNAVAILABLE';r['reason_codes']=['EVIDENCE_UNAVAILABLE']
        with self.assertRaises(ValueError):validate_execution(ROOT,d,b)
    def test_T05_psi429_local_lab_fallback_in_simulation(self):
        route=self.routes['PERF-02'];tmp=Path(self.temp.name)/('fallback-'+os.urandom(5).hex());tmp.mkdir()
        opts={'url':'https://example.org/','owner_authorized':False,'offline':False,'allow_api':True,'allow_lighthouse':True,'metric_index':12}
        calls={'api':0,'local':0}
        def fake_api(*args):
            calls['api']+=1;raise HTTPError('https://example.org/',429,'Too Many Requests',{},None)
        def fake_lh(url,factor):
            calls['local']+=1
            return {'outcome':'SUCCESS_RAW','observed_url':url,'artifacts':[('lab_json',b'{"lighthouseVersion":"unit", "audits":{}}')],
                'tool_name':'unit-mocked-lighthouse','tool_version':'unit','exit_code':0,'reason':'mocked lab JSON'}
        with patch.dict(os.environ,{'PIXELKIEZ_PAGESPEED_API_KEY':'unit-test-only'}),patch('run_48_core_metrics.google_capture',side_effect=fake_api),patch('run_48_core_metrics.lighthouse_capture',side_effect=fake_lh),patch('run_48_core_metrics.shutil.which',return_value='/unit/lighthouse'):
            row,_=execute_metric(tmp,'TEST-RUN-PSI429',self.registry['PERF-02'],route,opts,{},None)
        self.assertEqual((calls['api'],calls['local']),(1,1));self.assertEqual(len(row['execution_proof']['attempt_receipts']),2)
        self.assertEqual(row['execution_proof']['completion_state'],'ATTEMPTED')
        rr=json.loads((tmp/row['execution_proof']['attempt_receipts'][1]).read_text())
        self.assertEqual(rr['adapter'],'LIGHTHOUSE_CLI');self.assertEqual(rr['measurement_class'],'lab')
    def test_T06_three_failed_distinct_methods_local_simulation(self):
        route=copy.deepcopy(self.routes['FIND-01'])
        base=route['primary'];route['alternatives']=[]
        for n,adapter in enumerate(['PUBLIC_BROWSER','PUBLIC_SEARCH','MANUAL_EVIDENCE'],2):
            alt=copy.deepcopy(base);alt['route_id']=f'FIND-01-SYN-{n}';alt['method_id']=f'unit-failure-{n}';alt['adapter']=adapter
            route['alternatives'].append(alt)
        route['unavailable_fallback_slots']=[]
        tmp=Path(self.temp.name)/('three-'+os.urandom(5).hex());tmp.mkdir()
        def tool_fail(*args,**kwargs):
            opts=kwargs.get('opts') or (args[1] if len(args)>1 else {})
            return {'outcome':'TOOL_FAILURE','observed_url':'https://example.org/','artifacts':[('tool_log',b'UNIT: simulated nonzero tool failure')],
                'tool_name':'unit-fake-collector','tool_version':'unit','exit_code':9,'reason':'simulated tool failure'}
        with patch('run_48_core_metrics._outcome',side_effect=tool_fail):
            row,_=execute_metric(tmp,'TEST-THREE-FAILS',self.registry['FIND-01'],route,
               {'url':'https://example.org/','owner_authorized':False,'offline':False,'allow_api':False,'allow_lighthouse':False,'metric_index':1},{},None)
        self.assertEqual(row['execution_proof']['completion_state'],'VERIFIED_TOOL_FAILURE')
        self.assertEqual(len(row['execution_proof']['attempt_receipts']),4)
        self.assertEqual(len({json.loads((tmp/rel).read_text())['method_id'] for rel in row['execution_proof']['attempt_receipts']}),4)
        # This unit simulation does not prove the canonical catalog supports 3 production fallbacks.
    def test_T07_one_alternative_and_missing_slots_declared(self):
        route=self.routes['PERF-03'];self.assertEqual(len(route['alternatives']),1)
        self.assertEqual(len(route['unavailable_fallback_slots']),2)
        self.assertNotEqual(route['primary']['method_id'],route['alternatives'][0]['method_id'])
    def test_T08_owner_block_no_false_negative_score(self):
        row=next(r for r in self.bundle['results'] if r['metric_id']=='TRUST-08')
        self.assertEqual(row['execution_proof']['completion_state'],'VERIFIED_POLICY_BLOCKED')
        self.assertIsNone(row['value']);self.assertIsNone(row['product_status'])
        rel=row['execution_proof']['attempt_receipts'][0]
        attempt=json.loads((self.sample_dir/rel).read_text())
        self.assertEqual(attempt['tool']['name'],'permission-boundary')
        self.assertEqual(attempt['outcome'],'POLICY_BLOCKED')
    def test_T09_authoritative_404_simulation_never_yields_zero(self):
        def absent(*args,**kwargs):raise HTTPError('https://example.org/',404,'Not found',{},None)
        with patch.dict(os.environ,{'PIXELKIEZ_PAGESPEED_API_KEY':'unit-test-only'}),patch('measurement_adapters.fetch_crux',side_effect=absent),patch('core_capture.check_public',return_value=None):
            r=google_capture('https://example.org/','PUBLIC_CRUX','mobile')
        self.assertEqual(r['outcome'],'SOURCE_ABSENT')
        obj=json.loads(r['artifacts'][0][1]);self.assertEqual(obj['status_code'],404)
        self.assertNotIn('value',obj)
    def test_T10_tampered_sha_and_path_and_symlink(self):
        d,b=self.clone();rel=b['results'][0]['execution_proof']['attempt_receipts'][0]
        item=json.loads((d/rel).read_text());raw=d/item['artifacts'][0]['path']
        raw.write_bytes(raw.read_bytes()+b'x')
        with self.assertRaisesRegex(ValueError,'DIGEST'):validate_receipts(ROOT,d,b)
        d,b=self.clone();r=b['results'][0];r['execution_proof']['attempt_receipts']=['evidence/receipts/../../run-leak.json']
        with self.assertRaisesRegex(ValueError,'PATH_TRAVERSAL'):validate_receipts(ROOT,d,b)
        d,b=self.clone();r=b['results'][0];original=d/r['execution_proof']['attempt_receipts'][0]
        original.unlink();original.symlink_to(self.sample_dir/r['execution_proof']['attempt_receipts'][0])
        with self.assertRaisesRegex(ValueError,'SYMLINK'):validate_receipts(ROOT,d,b)
    def test_T11_cross_run_route_target_and_digest_mismatch(self):
        for key,value in [('execution_run_id','CROSS-RUN'),('target_url','https://wrong.example/')]:
            d,b=self.clone();b[key]=value
            with self.assertRaises(ValueError):validate_receipts(ROOT,d,b)
        d,b=self.clone();rel=b['results'][0]['execution_proof']['attempt_receipts'][0]
        p=d/rel;data=json.loads(p.read_text());data['method_version']='FAKE';p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):validate_receipts(ROOT,d,b)
        d,b=self.clone();rec=make_receipt(ROOT,d,b);self.assertEqual(rec['status'],'FAIL')
        with self.assertRaises(ValueError):validate_receipt(ROOT,d,dict(rec,registry_sha256='0'*64),require_live=False)
    def test_T12_freely_written_text_is_not_a_collector(self):
        d,b=self.clone();rel=b['results'][0]['execution_proof']['attempt_receipts'][0]
        p=d/rel;data=json.loads(p.read_text());data['tool']['name']='model';p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'MODEL_TEXT_IS_NOT_EXECUTOR'):validate_receipts(ROOT,d,b)
    def test_T13_cannot_falsely_close_48_and_admit_12(self):
        d,b=self.clone()
        for r in b['results']:
            r['execution_proof']['completion_state']='VERIFIED_UNAVAILABLE'
            r['execution_state']='UNAVAILABLE';r['value']=None;r['product_status']=None
            r['reason_codes']=['EVIDENCE_UNAVAILABLE']
        with self.assertRaises(ValueError):validate_execution(ROOT,d,b)
        # Positive 48/48 with 12 valid measurements requires actual authentic 48 closed-source run (NOT CLAIMED).
    def test_T14_customer_builder_requires_execution_receipt(self):
        src=ROOT/'evals/fixtures/full-48-active-golden-score.json'
        tmp=Path(self.temp.name)/('customer-'+os.urandom(4).hex())
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/build_audit_deliverables.py'),str(src),str(tmp),'--release-mode','customer'],text=True,capture_output=True,timeout=15)
        self.assertNotEqual(proc.returncode,0);self.assertIn('CUSTOMER_EXECUTION_COMPLETENESS_RECEIPT_REQUIRED',proc.stderr+proc.stdout)
        self.assertFalse(tmp.exists())
    def test_T15_finalizer_never_promotes_synthetic_old_manifest(self):
        d=Path(self.temp.name)/('finalize-'+os.urandom(5).hex());d.mkdir()
        (d/'deliverable-manifest.json').write_text(json.dumps({'status':'CUSTOMER_RELEASE_READY','customer_release_ready':True,'release_mode':'customer'}))
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/finalize_deliverable_manifest.py'),str(d)],text=True,capture_output=True,timeout=15)
        self.assertNotEqual(proc.returncode,0)
        obj=json.loads((d/'deliverable-manifest.json').read_text())
        self.assertNotEqual(obj.get('status'),'CUSTOMER_RELEASE_READY')
    def test_T16_shared_page_response_reused_without_second_network_call(self):
        tmp=Path(self.temp.name)/('reuse-'+os.urandom(5).hex());tmp.mkdir()
        calls=[]
        def single(url):
            calls.append(url);info={'requested_url':url,'observed_url':url,'status_code':200,'headers':{},'body_sha256':'x','body_bytes':8,'captured_at':'2026-10-30T00:00:00Z'}
            return {'outcome':'SUCCESS_RAW','observed_url':url,'artifacts':[('http_response',json.dumps(info).encode()),('html',b'<html/>')],
               'tool_name':'unit-http-collector','tool_version':'1','exit_code':0,'reason':'unit sample'}
        with patch('run_48_core_metrics.http_capture',side_effect=single):
            cache={};rows=[]
            for i,mid in enumerate(['FIND-01','FIND-03'],1):
                row,_=execute_metric(tmp,'TEST-CACHE-ONE',self.registry[mid],self.routes[mid],
                 {'url':'https://example.org/','owner_authorized':False,'offline':False,'allow_api':False,'allow_lighthouse':False,'metric_index':i},cache,None)
                rows.append(row)
        self.assertEqual(len(calls),1)
        self.assertEqual(rows[0]['execution_proof']['completion_state'],'ATTEMPTED')
        self.assertEqual(rows[1]['execution_proof']['completion_state'],'ATTEMPTED')
    def test_T09_real_zero_and_false_values_are_not_missing(self):
        tmp=Path(self.temp.name)/('zeros-'+os.urandom(5).hex());tmp.mkdir()
        url='https://example.org/'
        resp={'requested_url':url,'observed_url':url,'status_code':200,'headers':{},'body_sha256':'raw',
              'body_bytes':6,'captured_at':'2026-10-30T00:00:00Z'}
        def executed_response(*args):
            return {'outcome':'SUCCESS_RAW','observed_url':url,'artifacts':[('http_response',json.dumps(resp).encode())],
                    'tool_name':'mock-executed-http','tool_version':'unit','exit_code':0,'reason':'test: success'}
        assessment={'product_status':'strong','value':{'actual_count':0,'is_broken':False},
                    'rubric_observation':'Homepage returned a valid response on the sampled requested URL.',
                    'rubric_reason':'The actual zero and false are deliberate observable fixture values, not absent data.'}
        with patch('run_48_core_metrics.http_capture',side_effect=executed_response):
            row,ev=execute_metric(tmp,'UNIT-VALUES-ZERO',self.registry['FIND-01'],self.routes['FIND-01'],
                {'url':url,'owner_authorized':False,'offline':False,'allow_api':False,'allow_lighthouse':False,'metric_index':1},{},assessment)
        self.assertEqual(row['execution_proof']['completion_state'],'VERIFIED_RESULT')
        self.assertEqual(row['value']['actual_count'],0);self.assertIs(row['value']['is_broken'],False)
        self.assertIsNotNone(ev)
        mini={'schema_version':'2.0','mode':'LIVE','target_url':url,'execution_run_id':'UNIT-VALUES-ZERO','results':[row]}
        verified=validate_receipts(ROOT,tmp,mini)
        self.assertEqual(verified['FIND-01'][0]['outcome'],'SUCCESS_RAW')

    def test_T17_legacy_v1_fixture_remains_accepted(self):
        obj=json.loads((ROOT/'evals/fixtures/full-48-core-execution.json').read_text())
        self.assertIn(obj['mode'],{'FIXTURE','REPLAY'})
        validate_bundle(ROOT,obj)
    def test_T18_no_network_never_equals_production_PASS(self):
        self.assertEqual(len(self.bundle['results']),48)
        out=validate_execution(ROOT,self.sample_dir,self.bundle)
        self.assertEqual(out['execution_completeness'],'FAIL')
        self.assertLess(out['completed'],48)

if __name__=='__main__':unittest.main()
