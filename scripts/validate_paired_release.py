#!/usr/bin/env python3
"""Revalidate paired v1.3 evidence against current installed producer and consumer bytes."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path

def fail(msg): print('FAIL: '+msg,file=sys.stderr); return 1
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
    if len(argv)!=2:return fail('usage: validate_paired_release.py <website-skill-dir>')
    root=Path(argv[1]).resolve()
    try:r=json.loads((root/'reports/paired-release-report.json').read_text(encoding='utf-8'))
    except Exception as exc:return fail(f'paired report unreadable: {exc}')
    if r.get('status')!='PASS':return fail('paired release status is not PASS')
    consumer=Path(str(r.get('consumer_skill_dir') or '')).resolve()
    wp=root/'contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json'; vp=consumer/'contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json'
    if not vp.exists():return fail('actual consumer v1.3 contract missing')
    wd,vd=digest(wp),digest(vp)
    if wd!=vd:return fail(f'current producer/consumer digest mismatch {wd}!={vd}')
    c=json.loads(wp.read_text(encoding='utf-8'))
    if r.get('contract',{}).get('sha256')!=wd or r.get('contract',{}).get('version')!=c.get('version'):return fail('paired report is stale against current contract')
    if r.get('voice_release_harness',{}).get('status')!='PASS':return fail('voice harness evidence missing')
    if r.get('provider_neutral_packet_e2e')!='PASS' or r.get('truth_attack_e2e')!='PASS':return fail('cross-skill E2E evidence incomplete')
    print(f'PASS: paired release current digest={wd} consumer={consumer}')
    return 0
if __name__=='__main__':raise SystemExit(main(sys.argv))
