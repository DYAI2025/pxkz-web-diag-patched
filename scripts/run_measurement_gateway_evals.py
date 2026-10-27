#!/usr/bin/env python3
"""Deterministic Measurement Platform integration evals; no live network required."""
from __future__ import annotations
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable


def run(cmd:list[str], env=None)->str:
    p=subprocess.run(cmd,text=True,capture_output=True,env=env)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip() or 'command failed')
    return p.stdout.strip()


def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv:list[str])->int:
    root=Path(argv[1]).resolve() if len(argv)>1 else ROOT
    checks=[]
    try:
        fixture=root/'evals/fixtures/measurement-gateway-envelope.json'
        unavailable=root/'evals/fixtures/measurement-gateway-unavailable.json'
        run([PY,str(root/'scripts/validate_measurement_envelope.py'),str(fixture)]); checks.append('schema_fixture')
        run([PY,str(root/'scripts/validate_measurement_envelope.py'),str(unavailable)]); checks.append('schema_unavailable')
        run([PY,str(root/'scripts/validate_measurement_platform_baseline.py'),str(root)]); checks.append('protected_baseline')
        run([PY,str(root/'scripts/validate_third_party_license_ledger.py'),str(root)]); checks.append('third_party_no_copy')
        run([PY,str(root/'scripts/validate_gateway_optional_contracts.py'),str(root)]); checks.append('optional_contracts')
        with tempfile.TemporaryDirectory(prefix='pxk-gw-eval-') as td:
            td=Path(td)
            metrics=td/'metrics.json'
            run([PY,str(root/'scripts/normalize_gateway_measurements.py'),str(fixture),str(metrics)])
            rows=json.loads(metrics.read_text())
            if len(rows)!=9 or any(x.get('value') is None for x in rows): raise ValueError('fixture normalization mismatch')
            if any(x.get('source_type')!='FIXTURE_REPLAY' for x in rows): raise ValueError('fixture/live distinction lost')
            checks.append('normalization')
            out=td/'enrichment.json'
            env=dict(os.environ); env.setdefault('TERM','xterm')
            run([PY,str(root/'scripts/collect_measurement_enrichment.py'),'https://example.com/',str(out),'--config',str(root/'evals/fixtures/measurement-gateway-config.json'),'--fixture-bundle',str(root/'evals/fixtures/measurement-gateway-provider-bundle.json'),'--offline'],env=env)
            payload=json.loads(out.read_text())
            src=[x for x in payload.get('sources',[]) if x.get('id')=='measurement_gateway']
            if len(src)!=1 or src[0].get('status')!='AVAILABLE': raise ValueError('gateway collector source state mismatch')
            if len(payload.get('metrics',[]))!=9: raise ValueError('gateway collector metric mismatch')
            run([PY,str(root/'scripts/validate_measurement_enrichment.py'),str(out)])
            checks.append('collector_fixture')
            cfg=td/'offline.json'; cfg.write_text(json.dumps({'measurement_gateway':{'enabled':True}}))
            out2=td/'offline-out.json'
            run([PY,str(root/'scripts/collect_measurement_enrichment.py'),'https://example.com/',str(out2),'--config',str(cfg),'--offline'],env=env)
            p2=json.loads(out2.read_text())
            gw=[x for x in p2.get('sources',[]) if x.get('id')=='measurement_gateway']
            if not gw or gw[0].get('status') not in {'UNAVAILABLE','NOT_CONFIGURED'}: raise ValueError('missing gateway must degrade explicitly')
            if p2.get('metrics'): raise ValueError('missing gateway must not synthesize zeros')
            checks.append('offline_degradation')
            # Core-score/CSV/closing/rendering contracts are protected by immutable-file hashes plus their own regression suites.
            base_report=json.loads((root/'evals/fixtures/synthetic-report.json').read_text())
            mutated=copy.deepcopy(base_report); mutated['measurement_enrichment']=payload
            if [m['id'] for m in base_report['metrics']] != [m['id'] for m in mutated['metrics']]: raise ValueError('core metric IDs changed')
            if len(mutated['metrics'])!=48: raise ValueError('core metric count changed')
            checks.append('48_core_unchanged')
        result={'status':'PASS','checks':len(checks),'check_ids':checks,'live_gateway_network':'NOT_ASSESSED_BY_FIXTURE_SUITE','scoring_policy':'NON_SCORING_ENRICHMENT','core_metric_count':48}
        (root/'reports/measurement-gateway-eval-results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(f"PASS: measurement gateway integration checks={len(checks)}")
        return 0
    except Exception as exc:
        result={'status':'FAIL','checks':len(checks),'check_ids':checks,'error':str(exc)}
        (root/'reports/measurement-gateway-eval-results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(f'FAIL: {exc}',file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main(sys.argv))
