#!/usr/bin/env python3
"""Validate fail-closed Impressum customer-risk projection across reporting layers."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from legal_customer_projection import resolve_projection


def _load(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def _norm(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def _legal_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for finding in report.get("findings", []):
        if not isinstance(finding, dict):
            continue
        risk = finding.get("customer_risk") if isinstance(finding.get("customer_risk"), dict) else {}
        if risk.get("source") == "impressum_compliance":
            out.append(finding)
    return out


def validate(sidecar: dict[str, Any], report: dict[str, Any], model: dict[str, Any] | None = None, pdf_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    projection = resolve_projection(sidecar)
    legal_findings = _legal_findings(report)

    if projection.get("priority") == "INTERNAL_ONLY":
        # The sidecar holds no customer-relevant result: any legal customer risk in the report is unbacked.
        if legal_findings:
            errors.append(f"sidecar projection is INTERNAL_ONLY but report carries {len(legal_findings)} legal customer-risk finding(s)")
        return errors

    if len(legal_findings) != 1:
        errors.append(f"expected exactly one consolidated legal finding, got {len(legal_findings)}")
        return errors

    finding = legal_findings[0]
    risk = finding.get("customer_risk") if isinstance(finding.get("customer_risk"), dict) else {}
    required_refs = set(projection.get("legal_metric_refs", []))
    if risk.get("priority") != projection.get("priority"):
        errors.append("customer_risk priority does not match resolver")
    if risk.get("claim_state") != projection.get("claim_state"):
        errors.append("customer_risk claim_state does not match resolver")
    if risk.get("warning_label") != projection.get("warning_label"):
        errors.append("customer_risk warning label does not match resolver")
    if risk.get("group") != projection.get("group"):
        errors.append("customer_risk group does not match resolver")
    if list(risk.get("legal_metric_refs") or []) != list(projection.get("legal_metric_refs") or []):
        errors.append("customer_risk legal_metric_refs do not match resolver")
    if not required_refs.issubset(set(finding.get("metric_refs", []))):
        errors.append("legal metric refs missing from finding")
    if not all(str(finding.get(k) or "").strip() for k in ("client_observation", "client_impact", "client_action")):
        errors.append("legal finding customer copy incomplete")

    if projection.get("required") is not True:
        return errors

    if model is None:
        return errors

    fid = str(finding.get("id"))
    model_findings = [f for f in model.get("findings", []) if isinstance(f, dict)]
    ids = [str(f.get("id")) for f in model_findings]
    if fid not in ids:
        errors.append("mandatory legal risk missing from customer top-four findings")
        return errors

    selected = [str(x) for x in model.get("client_story", {}).get("selected_lever_ids", [])]
    if fid not in selected:
        errors.append("mandatory legal risk missing from selected_lever_ids")
    if projection.get("priority") == "MANDATORY_CRITICAL" and projection.get("group") == "PROVIDER_IDENTITY":
        if not selected or selected[0] != fid:
            errors.append("mandatory critical provider-identity risk must be lever rank 1")

    warning = str(projection.get("warning_label") or "")
    if _norm(model.get("cover", {}).get("blocker_note")) != _norm(warning):
        errors.append("mandatory legal warning missing from cover blocker note")

    mf = next((f for f in model_findings if str(f.get("id")) == fid), None)
    if not mf:
        errors.append("mandatory legal model finding missing")
        return errors
    action = _norm(mf.get("action"))
    roadmap_now = [_norm(x.get("action")) for x in model.get("roadmap", {}).get("now", []) if isinstance(x, dict)]
    if action and action not in roadmap_now:
        errors.append("mandatory legal action missing from roadmap.now")
    closing = [_norm(x) for x in model.get("closing", {}).get("actions", [])]
    if action and action.rstrip(".") not in {x.rstrip(".") for x in closing}:
        errors.append("mandatory legal action missing from closing actions")

    if pdf_path is not None:
        try:
            from pypdf import PdfReader
            text = "\n".join((page.extract_text() or "") for page in PdfReader(str(pdf_path)).pages)
            low = _norm(text)
            if _norm(warning) not in low:
                errors.append("mandatory legal warning not visible in final PDF")
            headline = _norm(mf.get("headline"))
            if headline and headline not in low:
                errors.append("mandatory legal lever headline not visible in final PDF")
        except Exception as exc:
            errors.append(f"PDF legal visibility check failed: {exc}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sidecar")
    ap.add_argument("diagnosis_report")
    ap.add_argument("client_model", nargs="?")
    ap.add_argument("pdf", nargs="?")
    args = ap.parse_args()
    try:
        sidecar = _load(args.sidecar)
        report = _load(args.diagnosis_report)
        model = _load(args.client_model) if args.client_model else None
        errors = validate(sidecar, report, model, Path(args.pdf) if args.pdf else None)
        if errors:
            raise ValueError("; ".join(errors))
        projection = resolve_projection(sidecar)
        print(f"PASS: legal projection priority={projection['priority']} required={projection['required']}")
        return 0
    except Exception as exc:
        print(f"FAIL: legal customer projection: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
