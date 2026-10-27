#!/usr/bin/env python3
"""Validate analysis_report JSON/Markdown completeness and canonical digest parity."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def main(argv:list[str])->int:
    if len(argv)!=4:
        print("FAIL: usage: validate_analysis_report_completeness.py <analysis.json> <analysis.md> <canonical.json>", file=sys.stderr); return 1
    jp, mp, cp = map(Path, argv[1:])
    try:
        data=json.loads(jp.read_text(encoding="utf-8")); canonical=json.loads(cp.read_text(encoding="utf-8")); md=mp.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr); return 1
    errors=[]
    if data.get("source_report_sha256") != sha(cp): errors.append("canonical digest mismatch")
    jids=[str(x.get("id")) for x in data.get("metrics",[]) if isinstance(x,dict)]
    cids=[str(x.get("id")) for x in canonical.get("metrics",[]) if isinstance(x,dict)]
    if sorted(jids)!=sorted(cids) or len(jids)!=len(set(jids)): errors.append("metric parity mismatch")
    missing=[mid for mid in jids if not re.search(rf"(?m)^#+\s+.*{re.escape(mid)}\b|<a[^>]+{re.escape(mid)}", md)]
    if missing: errors.append("markdown missing metrics: "+", ".join(missing[:10]))
    rec_ids={str(x.get("id")) for x in data.get("recommendations",[]) if isinstance(x,dict)}
    for metric in data.get("metrics",[]):
        for rid in metric.get("recommendation_refs",[]):
            if str(rid) not in rec_ids: errors.append(f"unknown recommendation ref {rid}")
    if errors:
        print("FAIL: " + " | ".join(errors), file=sys.stderr); return 1
    print(f"PASS: analysis completeness metrics={len(jids)} recommendations={len(rec_ids)}")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
