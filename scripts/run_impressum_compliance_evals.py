#!/usr/bin/env python3
from __future__ import annotations
import json, sys, traceback, tempfile, subprocess, hashlib
from pathlib import Path

def main(argv):
    if len(argv)!=2:
        print('FAIL: usage: run_impressum_compliance_evals.py <skill-dir>', file=sys.stderr); return 1
    root=Path(argv[1]).resolve()
    try:
        sys.path.insert(0,str(root/'scripts'))
        from impressum_compliance import assess_case
    except Exception as exc:
        print(f'RED: impressum engine unavailable: {exc}', file=sys.stderr); return 2
    data=json.loads((root/'evals/fixtures/impressum-compliance-cases.json').read_text())
    results=[]; failures=[]
    for case in data['cases']:
        try:
            out=assess_case(case['context'],case.get('observations',{}),root=root)
            exp=case.get('expect',{})
            mids=[x['metric_id'] for x in out.get('results',[]) if x.get('result_state') in {'ASSESSED_DEFECT','POSSIBLE_LEGAL_REVIEW'}]
            if 'metrics' in exp and any(m not in mids for m in exp['metrics']): raise AssertionError(f"metrics expected={exp['metrics']} got={mids}")
            if 'metrics' in exp and exp['metrics']==[] and mids: raise AssertionError(f"expected no metrics got={mids}")
            if 'iles' in exp and out['iles']['points']!=exp['iles']: raise AssertionError(f"iles expected={exp['iles']} got={out['iles']['points']}")
            if 'jurisdiction_status' in exp and out['jurisdiction']['status']!=exp['jurisdiction_status']: raise AssertionError('jurisdiction mismatch')
            if 'iles_critical_override' in exp and out['overrides']['iles_critical_override']!=exp['iles_critical_override']: raise AssertionError('critical override mismatch')
            if 'audit_priority_critical' in exp and out['overrides']['audit_priority_critical']!=exp['audit_priority_critical']: raise AssertionError('audit priority critical mismatch')
            if 'severity' in exp and not any(r.get('severity')==exp['severity'] for r in out['results']): raise AssertionError('severity mismatch')
            if 'result_state' in exp and not any(r.get('result_state')==exp['result_state'] for r in out['results']): raise AssertionError('result state mismatch')
            if 'defect' in exp and not any(r.get('defect_type')==exp['defect'] for r in out['results']): raise AssertionError('defect mismatch')
            if exp.get('source_needed') and not out.get('source_needed'): raise AssertionError('source_needed missing')
            if 'expected_penalty' in exp and out.get('enforcement_exposure',{}).get('expected_penalty') is not exp['expected_penalty']: raise AssertionError('expected penalty must stay null')
            text=json.dumps(out,ensure_ascii=False)
            if exp.get('forbid_text') and exp['forbid_text'] in text: raise AssertionError('forbidden text present')
            results.append({'id':case['id'],'status':'PASS','iles':out['iles']['points'],'metrics':mids})
        except Exception as exc:
            failures.append({'id':case['id'],'error':str(exc)})
            results.append({'id':case['id'],'status':'FAIL','error':str(exc)})
    integration=[]
    try:
        # Determinism: canonical output for same evidence must match byte-for-byte.
        probe=data['cases'][0]
        a=assess_case(probe['context'],probe.get('observations',{}),root=root)
        b=assess_case(probe['context'],probe.get('observations',{}),root=root)
        if json.dumps(a,ensure_ascii=False,sort_keys=True,separators=(',',':')) != json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')):
            raise AssertionError('determinism mismatch')
        integration.append({'id':'determinism','status':'PASS'})

        # Automatic voice-hook fallback must ignore legal metric refs.
        from build_elevenlabs_batch_csv import make_hook
        legal_finding={'id':'F-999','severity':'critical','metric_refs':['LEGAL-IMP-02'],'observation':'Legal review signal','client_observation':'Legal review signal','evidence':[{'id':'E-999'}],'business_relevance':{'text':'review'}}
        if make_hook(legal_finding, {'findings':[legal_finding]}) is not None:
            raise AssertionError('LEGAL finding became automatic voice hook')
        integration.append({'id':'voice_isolation','status':'PASS'})

        with tempfile.TemporaryDirectory(prefix='pxk-legal-eval-') as td:
            td=Path(td)
            # Projection firewall + score delta zero on identical 48-core metric inputs.
            side=assess_case(probe['context'],probe.get('observations',{}),root=root)
            sidep=td/'sidecar.json'; sidep.write_text(json.dumps(side,ensure_ascii=False,indent=2)+'\n')
            source=root/'evals/fixtures/synthetic-report.json'
            projected=td/'projected.json'
            proc=subprocess.run([sys.executable,str(root/'scripts/attach_impressum_findings.py'),str(source),str(sidep),str(projected)],text=True,capture_output=True)
            if proc.returncode: raise AssertionError('projection failed: '+(proc.stderr or proc.stdout))
            before=json.loads(source.read_text()); after=json.loads(projected.read_text())
            changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
            if not changed.issubset({'findings','sources','limitations','source_needed'}): raise AssertionError('projection mutated forbidden fields: '+','.join(sorted(changed)))
            val=subprocess.run([sys.executable,str(root/'scripts/validate_report_input.py'),str(projected)],text=True,capture_output=True)
            if val.returncode: raise AssertionError('projected report schema invalid: '+(val.stderr or val.stdout))
            sb=td/'score-before.json'; sa=td/'score-after.json'
            for src,dst in [(source,sb),(projected,sa)]:
                pr=subprocess.run([sys.executable,str(root/'scripts/compute_score.py'),str(src),str(dst)],text=True,capture_output=True)
                if pr.returncode: raise AssertionError('score regression command failed: '+(pr.stderr or pr.stdout))
            jb=json.loads(sb.read_text())['score_summary']; ja=json.loads(sa.read_text())['score_summary']
            for key in ('score','display_status','coverage_percent','category_scores'):
                if jb.get(key)!=ja.get(key): raise AssertionError('core score delta on '+key)
            if ja.get('blocker_present') is not True: raise AssertionError('supported critical legal finding did not use existing blocker path')
            integration.append({'id':'projection_firewall_core_score_delta_zero','status':'PASS','score':ja.get('score'),'coverage_percent':ja.get('coverage_percent'),'blocker_present':ja.get('blocker_present')})

            # Customer leakage/overclaim negative controls must fail closed.
            bad=td/'bad.txt'; bad.write_text('ILES 72 applicability_status expected_penalty Website ist rechtswidrig.')
            pr=subprocess.run([sys.executable,str(root/'scripts/validate_customer_output_guardrails.py'),str(bad)],text=True,capture_output=True)
            if pr.returncode==0: raise AssertionError('customer guardrail accepted legal internal metadata/overclaim')
            good=td/'good.txt'; good.write_text('Dringender rechtlicher Prüfbedarf. Für die abschließende Rechtsbewertung ist qualifizierte rechtliche Prüfung sinnvoll.')
            pr=subprocess.run([sys.executable,str(root/'scripts/validate_customer_output_guardrails.py'),str(good)],text=True,capture_output=True)
            if pr.returncode!=0: raise AssertionError('customer guardrail rejected bounded legal wording: '+(pr.stderr or pr.stdout))
            integration.append({'id':'customer_legal_guardrails','status':'PASS'})
    except Exception as exc:
        failures.append({'id':'INTEGRATION','error':str(exc)})
        integration.append({'id':'integration','status':'FAIL','error':str(exc)})

    report={'schema_version':'1.0','status':'PASS' if not failures else 'FAIL','case_count':len(results),'pass_count':sum(r['status']=='PASS' for r in results),'integration_checks':integration,'failures':failures,'results':results}
    (root/'reports/impressum-compliance-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if failures:
        for f in failures: print('FAIL:',f, file=sys.stderr)
        return 1
    print(f"PASS: impressum compliance evals ({len(results)})")
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
