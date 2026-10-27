#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
import jsonschema

def main(argv:list[str])->int:
    if len(argv)!=3:
        print('FAIL: usage: validate_core_score_admission.py <skill-dir> <admission.json>',file=sys.stderr); return 1
    root=Path(argv[1]).resolve(); p=Path(argv[2]).resolve()
    try:
        data=json.loads(p.read_text()); schema=json.loads((root/'schemas/core-score-admission-report.schema.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(data)
        if len({x.get('metric_id') for x in data['metrics']})!=48: raise ValueError('admission metrics not unique 48')
        if data['release_state']=='FULL_48_ACTIVE_PASS' and data['score_admitted']!=48: raise ValueError('FULL_48_ACTIVE_PASS requires score_admitted=48')
    except Exception as exc:
        print(f'FAIL: {exc}',file=sys.stderr); return 1
    print(f"PASS: score admission metrics=48 admitted={data['score_admitted']} state={data['release_state']}"); return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
