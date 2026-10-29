#!/usr/bin/env python3
"""Verify Measurement Platform baseline preservation across additive authorized patches.

Override reports form a hash chain from the frozen Measurement Platform baseline to
an explicitly authorized later patch.  A later override never weakens protection for
unlisted files: path, reason, baseline digest, previous digest (for chained changes),
and final candidate digest must all match.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_REASON_PATHS = {
    "CUSTOMER_LABEL_FIDELITY_PATCH": {
        "scripts/build_visualization_plan.py",
        "scripts/build_client_report_model.py",
    },
    "EVIDENCE_BOUND_CLAIMS_PATCH": {
        "scripts/client_story.py",
        "scripts/build_client_report_model.py",
        "scripts/build_visualization_plan.py",
        "scripts/build_audit_deliverables.py",
        "scripts/svg_chart_renderer.py",
        "templates/presentation.html.j2",
    },
    "CUSTOMER_SCOPE_STATEMENT_PATCH": {
        "templates/presentation.html.j2",
    },
    "CLAIM_SCOPE_PATCH": {
        "scripts/client_story.py",
        "scripts/build_visualization_plan.py",
    },
    "CUSTOMER_STATUS_COHERENCE_PATCH": {
        "scripts/build_visualization_plan.py",
    },
    "LEGAL_SURFACE_CUSTOMER_STATUS_PATCH": {
        "scripts/build_visualization_plan.py",
    },
    "CUSTOMER_LAYOUT_LEGAL_BOUNDARY_PATCH": {
        "assets/presentation.css",
        "templates/presentation.html.j2",
        "scripts/build_audit_deliverables.py",
    },
    "BRANCH_PRIORITY_VC03_CUSTOMER_RELEASE_PATCH": {
        "scripts/client_story.py",
        "scripts/build_client_report_model.py",
        "scripts/build_visualization_plan.py",
        "scripts/build_audit_deliverables.py",
    },
    "STRATEGIC_RELEVANCE_CUSTOMER_GUARDRAILS": {
        "scripts/client_story.py",
        "templates/client-report-template.json",
    },
    "CUSTOMER_PRESENTATION_QUALITY_GATE": {
        "scripts/client_story.py",
        "scripts/build_client_report_model.py",
        "scripts/build_visualization_plan.py",
        "scripts/build_audit_deliverables.py",
        "scripts/svg_chart_renderer.py",
        "templates/presentation.html.j2",
        "templates/client-report-template.json",
        "schemas/client-report.schema.json",
        "assets/presentation.css",
        "templates/visualizations/V03_TOP_LEVERS.vl.json",
    },
    "IMPRESSUM_COMPLIANCE_PATCH": {
        "scripts/build_audit_deliverables.py",
        "scripts/build_elevenlabs_batch_csv.py",
    },
    "PACKAGED_BRAND_FONT_PATCH": {
        "scripts/render_diagnosis_pdf.py",
        "scripts/build_audit_deliverables.py",
    },
    "IMPRESSUM_CUSTOMER_TRUTH_PATCH": {
        "scripts/client_story.py",
        "scripts/build_client_report_model.py",
        "scripts/build_audit_deliverables.py",
        "templates/presentation.html.j2",
        "assets/presentation.css",
    },
}

# Ordered oldest -> newest.  A later report may supersede an earlier override for
# the same path only by naming the immediately preceding digest.
OVERRIDE_REPORTS = (
    "reports/strategic-relevance-shared-overrides.json",
    "reports/impressum-compliance-shared-overrides.json",
    "reports/impressum-customer-truth-shared-overrides.json",
    "reports/branch-priority-vc03-shared-overrides.json",
    "reports/customer-layout-legal-boundary-shared-overrides.json",
    "reports/legal-surface-customer-status-shared-overrides.json",
    "reports/customer-status-coherence-shared-overrides.json",
    "reports/packaged-brand-font-shared-overrides.json",
    "reports/claim-scope-shared-overrides.json",
    "reports/customer-scope-statement-shared-overrides.json",
    "reports/customer-label-fidelity-shared-overrides.json",
    "reports/evidence-bound-claims-shared-overrides.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"override report is not an object:{path.relative_to(path.parents[1])}")
    return data


def _require_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"invalid_sha256:{label}")
    return value


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("FAIL: usage: validate_measurement_platform_baseline.py <skill-dir>", file=sys.stderr)
        return 1

    root = Path(argv[1]).resolve()
    try:
        baseline_path = root / "reports/measurement-platform-protected-baseline.json"
        data = _load_json(baseline_path)
        rows = data.get("protected_files", [])
        if not isinstance(rows, list) or not rows:
            raise ValueError("measurement platform protected_files missing or empty")

        baseline_by_path: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise ValueError("invalid protected baseline row")
            rel = row["path"]
            digest = _require_sha(row.get("sha256"), f"baseline:{rel}")
            if rel in baseline_by_path:
                raise ValueError(f"duplicate_protected_path:{rel}")
            baseline_by_path[rel] = digest

        effective = dict(baseline_by_path)
        override_counts = {rel: 0 for rel in baseline_by_path}
        applied_reports: list[str] = []

        for report_rel in OVERRIDE_REPORTS:
            report_path = root / report_rel
            if not report_path.is_file():
                continue
            report = _load_json(report_path)
            if report.get("status") != "PASS":
                raise ValueError(f"override_report_not_pass:{report_rel}")
            overrides = report.get("overrides", [])
            if not isinstance(overrides, list):
                raise ValueError(f"invalid_overrides_array:{report_rel}")
            seen_in_report: set[str] = set()
            for row in overrides:
                if not isinstance(row, dict):
                    raise ValueError(f"invalid_override_row:{report_rel}")
                rel = row.get("path")
                reason = row.get("reason")
                if not isinstance(rel, str) or rel not in baseline_by_path:
                    raise ValueError(f"unapproved_override_path:{rel}")
                if rel in seen_in_report:
                    raise ValueError(f"duplicate_override_in_report:{report_rel}:{rel}")
                seen_in_report.add(rel)

                allowed_paths = ALLOWED_REASON_PATHS.get(reason)
                if allowed_paths is None or rel not in allowed_paths:
                    raise ValueError(f"unapproved_override_reason:{rel}:{reason}")

                baseline_sha = _require_sha(row.get("baseline_sha256"), f"override_baseline:{rel}")
                current_sha = _require_sha(row.get("current_sha256"), f"override_current:{rel}")
                if baseline_sha != baseline_by_path[rel]:
                    raise ValueError(f"override_baseline_mismatch:{rel}")

                previous_sha = row.get("previous_sha256")
                if override_counts[rel] == 0:
                    if previous_sha is not None:
                        previous_sha = _require_sha(previous_sha, f"override_previous:{rel}")
                        if previous_sha != baseline_by_path[rel]:
                            raise ValueError(f"override_previous_mismatch:{rel}")
                else:
                    previous_sha = _require_sha(previous_sha, f"override_previous:{rel}")
                    if previous_sha != effective[rel]:
                        raise ValueError(f"override_chain_mismatch:{rel}")

                effective[rel] = current_sha
                override_counts[rel] += 1
            applied_reports.append(report_rel)

        errors: list[str] = []
        exact = 0
        intentional = 0
        chained = 0
        for rel, baseline_sha in baseline_by_path.items():
            path = root / rel
            if not path.is_file():
                errors.append(f"missing:{rel}")
                continue
            got = sha(path)
            expected = effective[rel]
            if got != expected:
                if override_counts[rel]:
                    errors.append(f"invalid_override:{rel}")
                else:
                    errors.append(f"changed:{rel}")
                continue
            if got == baseline_sha:
                exact += 1
            else:
                intentional += 1
                if override_counts[rel] > 1:
                    chained += 1

        if errors:
            raise ValueError(", ".join(errors))

        print(
            "PASS: protected baseline "
            f"exact={exact} intentional_shared_overrides={intentional} "
            f"chained_overrides={chained} override_reports={len(applied_reports)}"
        )
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
