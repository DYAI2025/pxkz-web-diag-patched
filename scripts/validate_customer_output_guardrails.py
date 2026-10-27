#!/usr/bin/env python3
"""Fail closed if internal audit/process metadata appears in customer-visible artifacts."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

FORBIDDEN = {
    "audit_coverage": r"(?:audit\s*coverage|audit[- ]?abdeckung|messabdeckung|testabdeckung)",
    "test_process": r"(?:labormessung|synthetische(?:r|s|n|m)?\s+(?:messwerte|messung|testreihe|daten)|testläuf|testreihe|messreihe|prüfpunkte|prüfumfang|testumfang|prüfverfahren|im\s+geprüften\s+umfang)",
    "evidence_meta": r"(?:evidence\s*grade|measurement\s*class|not_assessed|source_needed|belegstärke)",
    "qa_runtime": r"(?:\bvalidator(?:en|status)?\b|\bqa[- ]?status\b|\bfixture\b|\brenderer\b|\bruntime\b|release[- ]?gate|\bpipeline\b)",
    "visual_method_footer": r"(?:beweist\s+nicht\s*:|pixelkiez\s+bewertungsmodell|datenvisualisierung)",
    "provider_test_language": r"(?:\blabortest(?:s)?\b|\blighthouse\b|\bpagespeed\b|\bga4\b|google\s+analytics|serp\s+provider)",
    "legal_internal_metadata": r"(?:\bILES\b|applicability_status|legal_exposure_band|statutory_maximum|expected_penalty|iles_points)",
    "legal_overclaim": r"(?:Website ist rechtswidrig|versto(?:ß|ss)en definitiv|[0-9]+\s*%\s*(?:Rechtsverstoß|Illegalität)|rechtssicher|DSGVO[- ]?konform|erhalten\s+[0-9.]+\s*€\s*Strafe)",
}
RX = {name: re.compile(pattern, re.I) for name, pattern in FORBIDDEN.items()}


def visible_model(data: dict[str, Any]) -> object:
    return {
        "cover": data.get("cover"),
        "executive": data.get("executive"),
        "categories": data.get("categories"),
        "findings": [
            {k: f.get(k) for k in ("headline", "observation", "impact", "action")}
            for f in data.get("findings", []) if isinstance(f, dict)
        ],
        "roadmap": data.get("roadmap"),
        "recommendation": data.get("recommendation"),
        "closing": data.get("closing"),
    }


def text_from(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import fitz
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "cover" in data and "findings" in data:
            data = visible_model(data)
        return json.dumps(data, ensure_ascii=False)
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".html", ".htm", ".svg"}:
        raw = re.sub(r"<[^>]+>", " ", raw)
    return raw


def iter_paths(args: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in args:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in {".svg", ".html", ".pdf"}))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(raw)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("FAIL: usage: validate_customer_output_guardrails.py <customer artifact> [...]", file=sys.stderr)
        return 1
    try:
        paths = iter_paths(argv[1:])
        hits: list[str] = []
        for path in paths:
            text = text_from(path)
            for name, rx in RX.items():
                m = rx.search(text)
                if m:
                    hits.append(f"{path.name}:{name}:{m.group(0)}")
        if hits:
            raise ValueError("; ".join(hits))
        print(f"PASS: customer output guardrails artifacts={len(paths)}")
        return 0
    except Exception as exc:
        print(f"FAIL: customer output leakage: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
