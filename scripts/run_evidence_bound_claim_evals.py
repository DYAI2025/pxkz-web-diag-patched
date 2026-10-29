#!/usr/bin/env python3
"""Run the evidence-bound customer claims regression suite and write a digest-bound result.

Usage: run_evidence_bound_claim_evals.py <skill-root> [--json-out <path>]

The suite is tests/test_evidence_bound_claims.py (eight regression cases, golden pairs, mutation canary).
Exit 0 only when tests ran, none failed or errored and none were skipped: a skipped case (for example
without the PDF runtime) is NOT RUN, never a pass. The result binds to the tree digest of <skill-root>.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SUITE = "tests.test_evidence_bound_claims"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root")
    parser.add_argument("--json-out")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.json_out).resolve() if args.json_out else root / "reports/evidence-bound-claims-eval-results.json"
    digest_proc = subprocess.run([sys.executable, "-B", str(root / "scripts/pipeline_ledger.py"), "digest", str(root)],
                                 capture_output=True, text=True, cwd=root)
    digest = digest_proc.stdout.strip()
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", SUITE], capture_output=True, text=True, cwd=root)
    log = proc.stdout + proc.stderr
    ran_match = re.search(r"^Ran (\d+) tests?", log, re.M)
    ran = int(ran_match.group(1)) if ran_match else 0
    failures = int(m.group(1)) if (m := re.search(r"failures=(\d+)", log)) else 0
    errors = int(m.group(1)) if (m := re.search(r"errors=(\d+)", log)) else 0
    skipped = sorted(set(re.findall(r"^(\w+) \([^)]*\)\s*\n?.*?\.\.\. skipped", log, re.M)))
    results = re.findall(r"^(\w+) \(([\w.]+)\)[^\n]*?\.\.\. (ok|FAIL|ERROR|skipped[^\n]*)$", log, re.M)
    ok = proc.returncode == 0 and ran > 0 and not failures and not errors and not skipped and digest_proc.returncode == 0
    payload = {
        "schema_version": "1.0",
        "status": "PASS" if ok else "FAIL",
        "suite": SUITE,
        "artifact_digest": digest,
        "tests_run": ran,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        # Python >= 3.11 prints "name (module.Class.name)", older versions "name (module.Class)".
        "results": [{"test": cls if cls.endswith("." + name) else f"{cls}.{name}", "outcome": outcome.split()[0]}
                    for name, cls, outcome in results],
        "python": sys.version.split()[0],
        "does_not_prove": ["visual quality of a rendered PDF page", "behaviour on real customer audit data"],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{payload['status']}: {SUITE} ran={ran} failures={failures} errors={errors} skipped={len(skipped)} digest={digest[:12]}")
    if not ok:
        print(log[-3000:], file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
