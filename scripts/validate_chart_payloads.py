#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
from chart_contract import validate_visualizations
def main(argv):
    if len(argv)!=2: print("FAIL: usage: validate_chart_payloads.py <report-or-model.json>",file=sys.stderr); return 1
    try: d=json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except Exception as exc: print(f"FAIL: {exc}",file=sys.stderr); return 1
    errors=validate_visualizations(d.get("visualizations",[]))
    if errors:
        [print("FAIL: "+x,file=sys.stderr) for x in errors]; return 1
    print(f"PASS: {len(d.get('visualizations',[]))} chart payload(s) conform to V01-V12")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
