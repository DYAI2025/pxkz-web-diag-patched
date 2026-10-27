#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, json, sys
from pathlib import Path

def main(argv):
    if len(argv)!=2: print('FAIL: usage: validate_impressum_legal_sources.py <skill-dir>',file=sys.stderr); return 1
    root=Path(argv[1]); reg=json.loads((root/'assets/impressum-compliance-registry.v1.json').read_text())
    errors=[]; enabled=[]; disabled=[]
    today=dt.date(2026,9,8)
    for rule in reg.get('rules',[]):
        if rule.get('enabled'):
            enabled.append(rule['rule_id'])
            if rule.get('source_class')!='primary': errors.append(rule['rule_id']+': enabled non-primary')
            if not rule.get('source_url') or not rule.get('jurisdiction') or not rule.get('regime') or not rule.get('scope'): errors.append(rule['rule_id']+': incomplete rule binding')
            try: age=(today-dt.date.fromisoformat(rule['verified_at'])).days
            except Exception: errors.append(rule['rule_id']+': invalid verified_at'); continue
            if age>365: errors.append(rule['rule_id']+': stale primary source')
            if rule.get('source_status')!='VERIFIED': errors.append(rule['rule_id']+': enabled source status not VERIFIED')
        else:
            disabled.append(rule['rule_id'])
            if rule.get('source_status')!='SOURCE_NEEDED': errors.append(rule['rule_id']+': disabled release-1 adapter must be SOURCE_NEEDED')
    required={'EU-ECOM-2000-31-ART5','DE-DDG-5','DE-DDG-33','DE-EGBGB-246A-1'}
    if not required.issubset(set(enabled)): errors.append('release-1 core primary rules missing')
    research=(root/'references/source-map.md').read_text(encoding='utf-8')
    if 'user_provided' not in research or 'deep-research-report' not in research: errors.append('Deep Research user_provided classification missing from source-map')
    report={'status':'FAIL' if errors else 'PASS','verified_at':'2026-09-08','enabled_rules':enabled,'disabled_source_needed':disabled,'errors':errors}
    (root/'reports/impressum-legal-source-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if errors:
        for e in errors: print('FAIL:',e,file=sys.stderr)
        return 1
    print(f'PASS: impressum legal sources enabled={len(enabled)} disabled_source_needed={len(disabled)}')
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
