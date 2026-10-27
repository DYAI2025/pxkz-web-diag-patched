#!/usr/bin/env python3
"""Canonical reporting-bundle eval alias."""
from __future__ import annotations
import subprocess,sys
from pathlib import Path

def main(argv:list[str])->int:
    if len(argv)!=2:
        print('FAIL: usage: run_reporting_bundle_evals.py <skill-dir>',file=sys.stderr);return 1
    root=Path(argv[1]).resolve()
    return subprocess.run([sys.executable,str(root/'scripts/run_visual_architecture_evals.py'),str(root)]).returncode
if __name__=='__main__': raise SystemExit(main(sys.argv))
