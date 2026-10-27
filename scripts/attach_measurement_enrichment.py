#!/usr/bin/env python3
"""Attach a validated measurement-enrichment bundle to a canonical diagnosis report."""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT=Path(__file__).resolve().parents[1]
def norm(u:str)->str:
    p=urlsplit(str(u)); path=p.path.rstrip('/') or '/'; return urlunsplit((p.scheme.lower(),p.netloc.lower(),path,p.query,''))
def main(argv:list[str])->int:
    if len(argv)!=4:
        print('FAIL: usage: attach_measurement_enrichment.py <diagnosis.json> <enrichment.json> <output.json>',file=sys.stderr); return 1
    diagnosis,enrichment,out=map(Path,argv[1:])
    try:
        d=json.loads(diagnosis.read_text(encoding='utf-8')); e=json.loads(enrichment.read_text(encoding='utf-8'))
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/validate_measurement_enrichment.py'),str(enrichment)],text=True,capture_output=True)
        if proc.returncode: raise ValueError(proc.stderr.strip() or proc.stdout.strip())
        target=str(e.get('target_url') or ''); audited=str((d.get('meta') or {}).get('audited_url') or '')
        if norm(target)!=norm(audited): raise ValueError(f'target URL mismatch: enrichment={target} diagnosis={audited}')
        d['measurement_enrichment']=e
        out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/validate_report_input.py'),str(out)],text=True,capture_output=True)
        if proc.returncode: raise ValueError(proc.stderr.strip() or proc.stdout.strip())
        print(f'PASS: attached measurement enrichment metrics={len(e.get("metrics",[]))}')
        return 0
    except Exception as exc:
        print(f'FAIL: {exc}',file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main(sys.argv))
