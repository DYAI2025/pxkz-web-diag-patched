#!/usr/bin/env python3
"""Fail closed when internal audit language leaks into the customer model or PDF."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

FORBIDDEN = [
    r"\bcoverage\b", r"Messabdeckung", r"\bTests?\b", r"Testläuf", r"Testreihe", r"\bTestumfang\b", r"\bPrüfverfahren\b",
    r"\bEvidence\s*Grade\b", r"\bMeasurement\s*Class\b", r"\bnot_assessed\b",
    r"\bSOURCE_NEEDED\b", r"\bValidator(?:en|status)?\b", r"\bQA(?:-Status)?\b",
    r"\bconfidence\b", r"\bSicherheit:\s*(?:hoch|mittel|niedrig)\b", r"\bE[1-8]\b",
    r"\bMetric\s*ID\b", r"\bAudit-Pipeline\b", r"\bFixture\b", r"\bSimulation\b",
]
RX = [re.compile(p, re.I) for p in FORBIDDEN]

def extract(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import fitz
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)
    data = json.loads(path.read_text(encoding="utf-8"))
    visible = {
        "cover": data.get("cover"), "executive": data.get("executive"), "categories": data.get("categories"),
        "findings": [{k: f.get(k) for k in ("headline","observation","impact","action")} for f in data.get("findings", []) if isinstance(f, dict)],
        "roadmap": data.get("roadmap"), "recommendation": data.get("recommendation"), "closing": data.get("closing")
    }
    return json.dumps(visible, ensure_ascii=False)

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("FAIL: usage: validate_customer_business_language.py <client-model.json> [customer.pdf]", file=sys.stderr); return 1
    hits=[]
    for raw in argv[1:]:
        path=Path(raw)
        text=extract(path)
        for rx in RX:
            if rx.search(text): hits.append(f"{path.name}:{rx.pattern}")
    if hits:
        print("FAIL: internal customer-language leakage: " + ", ".join(hits), file=sys.stderr); return 1
    print("PASS: customer business language firewall")
    return 0
if __name__ == "__main__": raise SystemExit(main(sys.argv))
