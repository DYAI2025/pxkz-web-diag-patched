#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from core_active_measurement import materialize_report

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('skill_dir'); ap.add_argument('base_report'); ap.add_argument('execution_bundle'); ap.add_argument('output_report'); ap.add_argument('--admission-out',required=True)
    a=ap.parse_args(); root=Path(a.skill_dir).resolve()
    try:
        base=json.loads(Path(a.base_report).read_text(encoding='utf-8')); bundle=json.loads(Path(a.execution_bundle).read_text(encoding='utf-8'))
        out,admission=materialize_report(root,base,bundle)
        Path(a.output_report).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        Path(a.admission_out).write_text(json.dumps(admission,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"PASS: materialized core metrics=48 score_admitted={admission['score_admitted']} release={admission['release_state']}")
        return 0
    except Exception as exc:
        print(f'FAIL: {exc}'); return 1
if __name__=='__main__': raise SystemExit(main())
