#!/usr/bin/env python3
"""Create and verify a minimal hash-chained enterprise build ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_boundary import excluded  # noqa: E402  (shared with the v3.2.1 check and package_skill)

STAGES = [
    "INTAKE_COMPLETED",
    "RESEARCH_COMPLETED",
    "CAPABILITY_DECISION_SKIPPED",
    "ARCHITECTURE_GATE_PASSED",
    "DRAFT_FROZEN",
    "RELEASE_GATE_PASSED",
    "EVALUATOR_PASSED",
    "VALIDATION_PASSED",
    "PACKAGE_AUTHORIZED",
]


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_tree(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if excluded(rel):
            continue
        h.update(str(rel).replace(os.sep, "/").encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def event_hash(event_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(event_without_hash)).hexdigest()


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception as exc:
            raise ValueError(f"invalid ledger JSON at line {line_no}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"ledger line {line_no} is not an object")
        events.append(item)
    return events


def verify(events: list[dict[str, Any]], current_digest: str | None = None) -> tuple[bool, str]:
    prev = "GENESIS"
    for idx, event in enumerate(events, 1):
        if event.get("seq") != idx:
            return False, f"sequence mismatch at event {idx}"
        if event.get("prev_hash") != prev:
            return False, f"prev_hash mismatch at event {idx}"
        given = event.get("event_hash")
        body = dict(event)
        body.pop("event_hash", None)
        expected = event_hash(body)
        if given != expected:
            return False, f"event_hash mismatch at event {idx}"
        prev = given
    if current_digest and events:
        freeze = next((e for e in reversed(events) if e.get("event_type") == "DRAFT_FROZEN"), None)
        if freeze and freeze.get("artifact_digest") != current_digest:
            return False, "STALE_ARTIFACT_DIGEST"
        if freeze:
            for event in events[events.index(freeze) + 1 :]:
                if event.get("event_type") in {"RELEASE_GATE_PASSED", "EVALUATOR_PASSED", "VALIDATION_PASSED", "PACKAGE_AUTHORIZED"}:
                    if event.get("artifact_digest") != freeze.get("artifact_digest"):
                        return False, f"digest mismatch at {event.get('event_type')}"
    return True, "PASS"


def append_event(path: Path, run_id: str, event_type: str, artifact_digest: str | None, data: dict[str, Any]) -> dict[str, Any]:
    events = read_events(path)
    ok, reason = verify(events)
    if not ok:
        raise ValueError(reason)
    seq = len(events) + 1
    prev_hash = events[-1]["event_hash"] if events else "GENESIS"
    event = {
        "seq": seq,
        "run_id": run_id,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifact_digest": artifact_digest,
        "data": data,
        "prev_hash": prev_hash,
    }
    event["event_hash"] = event_hash(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_digest = sub.add_parser("digest")
    p_digest.add_argument("skill_dir")
    p_append = sub.add_parser("append")
    p_append.add_argument("skill_dir")
    p_append.add_argument("ledger")
    p_append.add_argument("run_id")
    p_append.add_argument("event_type", choices=STAGES)
    p_append.add_argument("--with-digest", action="store_true")
    p_append.add_argument("--status", default="PASS")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("skill_dir")
    p_verify.add_argument("ledger")
    args = parser.parse_args()

    root = Path(args.skill_dir).resolve()
    if args.cmd == "digest":
        print(digest_tree(root))
        return 0
    ledger = Path(args.ledger).resolve()
    if args.cmd == "append":
        digest = digest_tree(root) if args.with_digest else None
        event = append_event(ledger, args.run_id, args.event_type, digest, {"status": args.status})
        print(f"APPENDED: {event['seq']} {event['event_type']}")
        return 0
    events = read_events(ledger)
    ok, reason = verify(events, digest_tree(root))
    if not ok:
        print(f"FAIL: {reason}", file=sys.stderr)
        return 1
    print(f"PASS: ledger ({len(events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
