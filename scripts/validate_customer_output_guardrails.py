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

# Claim scope (PXK-BUG-001). Public pages are sampled, so an observation never reads as a whole-site fact
# (SEM-001); content inspection measures extractability and answerability, never AI answers, citations or
# rankings (SEM-002; registry limitations AI-01/AI-03/AI-06).
_AI_PLACE = r"(?:KI-Antworten|KI-Suchen?|KI-Ergebnissen|KI-Assistenten|ChatGPT|Gemini|Perplexity|Copilot)\b"
_SEEN = r"(?:sichtbar|genannt|zitiert|empfohlen|platziert|gelistet|gefunden|erschein|auftauch|taucht|tauchen|vorkomm)\w*"
CLAIM_RX = {
    "ai_visibility_overclaim": re.compile(
        r"KI-?/?\s*(?:Such)?(?:sichtbarkeit|ranking|platzierung|empfehlung|nennung|zitierung|zitation|traffic)\w*"
        r"|\b(?:die\s+KI|KI-Systeme?|KI-Assistenten?|KI-Suchen?|ChatGPT|Gemini|Perplexity|Copilot)\s+(?:\w+\s+)?"
        r"(?:nennt|nennen|zitiert|zitieren|empfiehlt|empfehlen|versteht|verstehen|kennt|kennen|bevorzugt|bevorzugen"
        r"|listet|listen|übersieht|übersehen|ignoriert|ignorieren)\b"
        rf"|{_SEEN}\s+(?:\w+\s+){{0,3}}(?:in|bei|von)\s+{_AI_PLACE}"
        rf"|\b(?:in|bei|von)\s+{_AI_PLACE}\s+(?:\w+\s+){{0,3}}(?:{_SEEN}|auf\b|vor\b|seltener|häufiger)"
        r"|für\s+KI-Systeme\s+(?:ist|sind|wirkt|wirken|erscheint)\b|\bwie\s+\w+\s+(?:die\s+)?Website\s+für\s+KI",
        re.I),
    "universal_scope": re.compile(
        r"auf\s+(?:allen|jeder|sämtlichen)\s+\w*seiten?\b|auf\s+der\s+gesamten\s+(?:Website|Webseite|Seite|Präsenz)"
        r"|überall\s+(?:gleich|identisch|einheitlich|konsistent|vorhanden|sichtbar)"
        r"|\b(?:jede|alle)\s+\w*seiten?\s+(?:zeigt|zeigen|ist|sind|hat|haben|nennt|nennen|fehlt|fehlen|enthält|enthalten)\b"
        r"|durchgängig\s+(?:gleich|einheitlich|identisch|konsistent)|websiteweit"
        r"|seitenübergreifend\s+(?:gleich|einheitlich|konsistent|identisch)",
        re.I),
}
# A sentence that states the measurement boundary ("... wurde nicht gemessen") is a disclaimer, not a claim.
DISCLAIMER = re.compile(r"nicht\s+(?:gemessen|belegt|geprüft|nachgewiesen|untersucht)|belegen?\s+keine|kein(?:en)?\s+Nachweis", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def claim_violations(text: str, *, scope: bool = True) -> list[tuple[str, str]]:
    """Claim-scope hits per sentence; ``scope=False`` skips the whole-site check (target-state actions)."""
    hits: list[tuple[str, str]] = []
    for sentence in SENTENCE.split(text):
        if DISCLAIMER.search(sentence):
            continue
        for name, rx in CLAIM_RX.items():
            if name == "universal_scope" and not scope:
                continue
            m = rx.search(sentence)
            if m:
                hits.append((name, m.group(0)))
    return hits


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


def observation_model(data: dict[str, Any]) -> object:
    """Customer statements about the observed state; actions and closing steps describe a target state."""
    return {
        "cover": data.get("cover"),
        "executive": data.get("executive"),
        "categories": data.get("categories"),
        "findings": [
            {k: f.get(k) for k in ("headline", "observation", "impact")}
            for f in data.get("findings", []) if isinstance(f, dict)
        ],
    }


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def claim_text(path: Path) -> tuple[str, bool]:
    """Text checked for claim scope and whether the whole-site check applies to it.

    The model is checked field by field (observations with the scope check); the SVG charts carry the row
    labels. HTML and PDF render the same model fields and cannot separate actions from observations, so they
    get the AI-visibility check only.
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "cover" in data and "findings" in data:
            return "\n".join(_strings(observation_model(data))), True
        return "\n".join(_strings(data)), True
    return text_from(path), suffix == ".svg"


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
            claims, scoped = claim_text(path)
            hits.extend(f"{path.name}:{name}:{match}" for name, match in claim_violations(claims, scope=scoped))
        if hits:
            raise ValueError("; ".join(hits))
        print(f"PASS: customer output guardrails artifacts={len(paths)}")
        return 0
    except Exception as exc:
        print(f"FAIL: customer output leakage: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
