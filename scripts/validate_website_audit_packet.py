#!/usr/bin/env python3
import json,sys
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parent.parent

def main(argv):
    if len(argv)!=2: print('FAIL: usage: validate_website_audit_packet.py <packet.json>',file=sys.stderr); return 1
    data=json.loads(Path(argv[1]).read_text(encoding='utf-8')); schema=json.loads((ROOT/'schemas/website-audit-packet.schema.json').read_text(encoding='utf-8')); errs=sorted(Draft202012Validator(schema).iter_errors(data),key=lambda e:list(e.path))
    if errs:
        for e in errs: print('FAIL: '+e.message,file=sys.stderr)
        return 1
    print(f"PASS: provider-neutral audit packet hooks={len(data.get('conversation_hooks',[]))}")
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
