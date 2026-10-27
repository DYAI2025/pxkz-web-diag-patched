#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
from client_story import visible_text
from customer_story_semantics import GENERIC_COPY, TECH_JARGON, model_finding_semantic_errors

FORBIDDEN = re.compile(r"\b(?:DERIVED|NONE_OFFICIAL|SITE|targeted_modernization|needs_action|not_assessed|findability_seo|ux_conversion|ai_readiness|CATEGORY:[A-Z_]+|(?:AI|UX|TRUST|FIND|PERF|A11Y)-\d+|E[1-8])\b", re.I)
BAD_GERMAN = re.compile(r"\b(?:authoritative|synchronisieren|Proof Points?|Conversion)\b", re.I)
AWKWARD_COPY = re.compile(r"(?:Stichprobensample|reale Nutzerdaten/reale Nutzerdaten|Besucherdaten/Kundendaten|Maschinen finden)", re.I)
PRIVACY_OVERCLAIM = re.compile(r"(?:DSGVO[- ]?konform|rechtssicher|rechtskonform|Website ist rechtswidrig|versto(?:ß|ss)en definitiv|[0-9]+\s*%\s*(?:Rechtsverstoß|Illegalität)|erhalten\s+[0-9.]+\s*€\s*Strafe|Einwilligungen?.{0,30}(?:\bOK\b|\bklar\b|konform))", re.I)

def main(argv:list[str])->int:
    if len(argv)!=2:
        print("FAIL: usage: validate_client_semantics.py <client-report-model.json>", file=sys.stderr); return 1
    data=json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    customer_visible_keys=("cover","executive","categories","client_story","findings","roadmap","recommendation","closing")
    customer_visible={key:data.get(key) for key in customer_visible_keys if key in data}
    text=visible_text(customer_visible)
    errors=[]
    if "…" in text or "..." in text: errors.append("semantic truncation marker found")
    m=FORBIDDEN.search(text)
    if m: errors.append("internal token visible: "+m.group(0))
    m=BAD_GERMAN.search(text)
    if m: errors.append("untranslated/awkward customer jargon visible: "+m.group(0))
    m=GENERIC_COPY.search(text)
    if m: errors.append("generic agency wording visible: "+m.group(0))
    m=TECH_JARGON.search(text)
    if m: errors.append("customer-facing technical jargon visible: "+m.group(0))
    m=AWKWARD_COPY.search(text)
    if m: errors.append("awkward customer wording visible: "+m.group(0))
    m=PRIVACY_OVERCLAIM.search(text)
    if m: errors.append("privacy/legal certainty exceeds public-surface evidence: "+m.group(0))
    closing = data.get("closing", {}) if isinstance(data.get("closing"), dict) else {}
    actions = closing.get("actions", []) if isinstance(closing.get("actions"), list) else []
    if len(actions) != 4:
        errors.append("closing must contain exactly four approved actions")
    for idx, action in enumerate(actions, 1):
        value = " ".join(str(action or "").split())
        if not value or value[-1:] not in ".!?":
            errors.append(f"closing.actions[{idx}] must be a complete terminated action")
    semantic=data.get("semantic_story")
    if not isinstance(semantic,dict) or semantic.get("status") != "PASS":
        errors.append("semantic_story must be PASS before rendering")
    if isinstance(semantic,dict) and semantic.get("errors"):
        errors.append("semantic_story contains errors")
    for finding in data.get("findings",[]):
        if isinstance(finding,dict): errors.extend(model_finding_semantic_errors(finding))
    global_limits = []
    executive = data.get("executive", {}) if isinstance(data.get("executive"), dict) else {}
    global_limits.append(("executive.takeaway", executive.get("takeaway", ""), 135))
    for idx, value in enumerate(executive.get("strengths", []) if isinstance(executive.get("strengths"), list) else [], 1):
        global_limits.append((f"executive.strengths[{idx}]", value, 110))
    for idx, value in enumerate(executive.get("priorities", []) if isinstance(executive.get("priorities"), list) else [], 1):
        global_limits.append((f"executive.priorities[{idx}]", value, 110))
    for idx, value in enumerate(data.get("categories", []) if isinstance(data.get("categories"), list) else [], 1):
        if isinstance(value, dict): global_limits.append((f"categories[{idx}].summary", value.get("summary", ""), 110))
    roadmap = data.get("roadmap", {}) if isinstance(data.get("roadmap"), dict) else {}
    for bucket, rows in roadmap.items():
        if isinstance(rows, list):
            for idx, row in enumerate(rows, 1):
                if isinstance(row, dict): global_limits.append((f"roadmap.{bucket}[{idx}]", row.get("action", ""), 125))
    recommendation = data.get("recommendation", {}) if isinstance(data.get("recommendation"), dict) else {}
    global_limits.append(("recommendation.reason", recommendation.get("reason", ""), 135))
    global_limits.append(("recommendation.next_step", recommendation.get("next_step", ""), 125))
    for name, value, limit in global_limits:
        text_value = " ".join(str(value or "").split())
        if len(text_value) > limit: errors.append(f"{name} exceeds scan-first limit {limit}")
    if errors:
        for e in errors: print("FAIL: "+e, file=sys.stderr)
        return 1
    print(f"PASS: scan-first customer semantics ({len(data.get('findings', []))} findings, {semantic.get('quantitative_signal_count', 0)} numeric signals)")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv))
