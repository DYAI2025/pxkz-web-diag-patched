#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
from core_active_measurement import ContractError,semantic_digest,validate_bundle

def main(argv:list[str])->int:
    if len(argv)!=3:
        print('FAIL: usage: validate_core_execution_bundle.py <skill-dir> <bundle.json>',file=sys.stderr); return 1
    root=Path(argv[1]).resolve(); path=Path(argv[2]).resolve()
    try:
        bundle=json.loads(path.read_text(encoding='utf-8')); validate_bundle(root,bundle)
    except Exception as exc:
        print(f'FAIL: {exc}',file=sys.stderr); return 1
    print(f'PASS: core execution bundle metrics=48 semantic_digest={semantic_digest(bundle)}'); return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
