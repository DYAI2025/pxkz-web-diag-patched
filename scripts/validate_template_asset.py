#!/usr/bin/env python3
from pathlib import Path
import hashlib,sys
EXPECTED="1fcde5007f6ef92967dd7caa740bec86df8f9f7239909a23aac5c06259205e8c"
def main(argv):
 root=Path(argv[1] if len(argv)>1 else ".").resolve(); p=root/"assets/PXK_web_audit_template.pdf"
 if not p.is_file(): print("FAIL: template PDF missing",file=sys.stderr); return 1
 got=hashlib.sha256(p.read_bytes()).hexdigest()
 if got!=EXPECTED: print(f"FAIL: template digest drift {got}",file=sys.stderr); return 1
 print("PASS: normative PXK web audit template asset")
 return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
