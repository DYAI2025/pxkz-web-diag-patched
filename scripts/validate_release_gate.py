#!/usr/bin/env python3
"""Validate the Pixelkiez Website Diagnosis release gate for the visual/reporting architecture."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import sys
from pathlib import Path

from semantic_release_evidence import semantic_bundle_digest


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def tree_digest(root: Path) -> str:
    return subprocess.check_output(
        [sys.executable, str(root / "scripts" / "pipeline_ledger.py"), "digest", str(root)],
        text=True,
    ).strip()


def _contract(root: Path) -> tuple[str, dict]:
    path = root / "contracts" / "pixelkiez-elevenlabs-batch-contract-v1.3.json"
    return hashlib.sha256(path.read_bytes()).hexdigest(), json.loads(path.read_text(encoding="utf-8"))


def validate_reports(root: Path, report: dict, paired: dict, semantic: dict, proof_pdfs: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Cross-skill, paired-release and customer-semantic evidence binding (fail closed).

    A claimed PASS must be backed by digest-consistent paired evidence; a blocked
    dependency is accepted only when it is declared non-package-blocking and the
    website side passed. Customer-semantic evidence must be PASS and bound to the
    current semantic control bundle.
    """
    errors: list[str] = []
    digest, contract = _contract(root)
    version = str(contract.get("version", ""))
    cross = report.get("cross_skill_dependency") or {}
    status = cross.get("status")
    if cross.get("website_skill_side_status") != "PASS":
        errors.append("website side of batch contract not validated")
    if status == "PASS":
        if cross.get("voice_architect_side_status") != "PASS":
            errors.append("cross-skill PASS without voice-architect side PASS")
        if cross.get("shared_v1_3_sha256") != digest:
            errors.append("cross-skill shared contract digest mismatch")
        if cross.get("shared_contract_version") != version:
            errors.append("cross-skill shared contract version mismatch")
        if cross.get("website_fields") != cross.get("voice_fields"):
            errors.append("cross-skill field count mismatch")
        pc = paired.get("contract") or {}
        if paired.get("status") != "PASS":
            errors.append("paired release evidence is not PASS")
        if pc.get("sha256") != digest or pc.get("version") != version:
            errors.append("paired release evidence stale against current contract")
        if (paired.get("voice_release_harness") or {}).get("status") != "PASS":
            errors.append("paired voice harness evidence missing")
        if paired.get("truth_attack_e2e") != "PASS" or paired.get("provider_neutral_packet_e2e") != "PASS":
            errors.append("paired cross-skill E2E evidence incomplete")
    elif status != "BLOCKED_DEPENDENCY_NON_PACKAGE_BLOCKING":
        errors.append("cross-skill dependency status invalid")

    errors.extend(validate_customer_report_release(root, report, semantic, proof_pdfs))
    return errors


def validate_customer_report_release(root: Path, report: dict, semantic: dict, proof_pdfs: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """CUSTOMER_REPORT_RELEASE: a customer PDF built from a real audit, never a proof (release-gate-policy.md).

    PASS needs customer semantic QA on a real audit input built in customer mode, bound to the live semantic bundle
    and tree. BLOCKED_NO_REAL_AUDIT_INPUT is a valid state that does not block the skill package, but then nothing
    may claim customer readiness, and no semantic PASS may come from proof or example data.

    data_class is a recorded label, so a PASS is also bound to an audit input that is no file of this skill tree
    (every example input ships in it), to a PDF that is none of the proof PDFs, and to a record without fixture
    provenance. The gate cannot prove an external audit is real beyond that; customer mode refusing example data
    (SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT) is the build-time guard.
    """
    errors: list[str] = []
    decision = report.get("customer_report_release") or {}
    status = decision.get("status")
    real = semantic.get("release_mode") == "customer" and semantic.get("data_class") == REAL_AUDIT_INPUT
    gate = report.get("customer_semantic_gate") or {}
    claims = (semantic.get("status"), semantic.get("semantic_qa_validation"), gate.get("status"))
    if not real and any(_claims_pass(x) for x in claims):
        errors.append("customer semantic PASS recorded on proof or example data")
    if status == CUSTOMER_REPORT_BLOCKED:
        if decision.get("package_blocking") is not False:
            errors.append("blocked customer report release must be declared non-package-blocking")
        if decision.get("customer_release_ready") is not False:
            errors.append("blocked customer report release cannot be customer-release-ready")
        ready = sorted(k for k, v in report.items() if isinstance(v, dict) and v.get("customer_release_ready") is True)
        if ready:
            errors.append(f"customer report release is blocked but {', '.join(ready)} claims customer readiness")
        semantic_pass = sorted(k for k, v in report.items() if isinstance(v, dict) and _claims_pass(v.get("semantic_qa")))
        if semantic_pass:
            errors.append(f"customer report release is blocked but {', '.join(semantic_pass)} claims a semantic PASS")
        return errors
    if status != "PASS":
        errors.append("customer report release status invalid")
        return errors
    if not real:
        errors.append("customer report release PASS without a real audit input built in customer mode")
    if {"fixture", "fixture_sha256"} & set(semantic):
        errors.append("customer report release PASS on a record with fixture provenance")
    audit, pdf = semantic.get("audit_input_sha256"), semantic.get("pdf_sha256")
    if not _is_sha256(audit) or audit in _tree_file_hashes(root):
        errors.append("customer report release PASS needs an audit input that is not a file of the skill tree")
    if not _is_sha256(pdf) or pdf in proof_pdfs:
        errors.append("customer report release PASS needs a customer PDF that is none of the proof PDFs")
    current = semantic_bundle_digest(root)
    if gate.get("status") != "PASS":
        errors.append("customer semantic gate is not PASS")
    if gate.get("semantic_bundle_sha256") != current:
        errors.append("customer semantic gate bound to a different semantic bundle")
    if semantic.get("status") != "PASS" or semantic.get("semantic_qa_validation") != "PASS" or semantic.get("visual_qa_validation") != "PASS":
        errors.append("customer semantic QA evidence is not PASS")
    if semantic.get("semantic_bundle_sha256") != current:
        errors.append("customer semantic QA evidence stale against current semantic bundle")
    # The semantic bundle omits rendering code (CSS, templates, plan builder), so rendered QA must also be
    # bound to the whole build-controlled tree it was inspected on.
    build = tree_digest(root)
    if semantic.get("artifact_digest") != build:
        errors.append("customer semantic QA evidence not bound to the current build artifact digest")
    if gate.get("artifact_digest") != build:
        errors.append("customer semantic gate not bound to the current build artifact digest")
    return errors


def validate_gate_statuses(report: dict) -> list[str]:
    """Release decision, judgment gates and every measured gate the package needs must read PASS."""
    errors: list[str] = []
    if report.get("release_scope") != "website-diagnosis-package": errors.append("release scope drift")
    if report.get("release_gate", {}).get("status") != "PASS": errors.append("release status is not PASS")
    if report.get("release_gate", {}).get("allowed_to_package") is not True: errors.append("allowed_to_package must be true")
    if report.get("craftsmanship_gate", {}).get("status") != "PASS": errors.append("craftsmanship gate failed")
    if report.get("anti_confabulation_gate", {}).get("status") != "PASS": errors.append("anti-confabulation gate failed")
    if report.get("anti_confabulation_gate", {}).get("blocked_claims"): errors.append("blocked_claims must be empty")
    syco = report.get("anti_sycophancy", {})
    if type(syco.get("score")) is not int or not 0 <= syco["score"] < ANTI_SYCOPHANCY_THRESHOLD or syco.get("threshold") != ANTI_SYCOPHANCY_THRESHOLD:
        errors.append("anti-sycophancy threshold failed")
    if report.get("bias_gate", {}).get("status") != "PASS": errors.append("bias gate is not PASS")
    browser = report.get("browser_gate", {})
    if browser.get("applicable") and browser.get("status") not in {"PASS", "PASS_WITH_ASSUMPTIONS"}: errors.append("browser gate failed")
    if browser.get("blockers"): errors.append("browser blockers must be empty")

    for gate_name in (
        "batch_contract_gate", "batch_evals_gate", "core_regression_gate", "internal_report_gate",
        "active_core_gate", "active_core_render_gate",
        "visualization_reporting_gate", "weasyprint_render_gate", "brand_rendering_gate", "proof_output_gate",
        "measurement_gateway_gate", "protected_baseline_gate", "third_party_reuse_gate", "measurement_platform_proof_gate",
        "strategic_relevance_gate", "customer_output_guardrail_gate", "measurement_platform_preservation_gate",
        "customer_presentation_quality_gate",
        "impressum_legal_source_gate", "impressum_compliance_gate", "impressum_eval_gate", "impressum_customer_projection_gate",
        "installability_gate", "test_suite_gate", "measurement_enrichment_gate", "customer_warning_semantics_gate",
        "customer_closing_gate", "measurement_platform_baseline_gate", "protected_candidate_gate",
        "strategic_relevance_preservation_gate", "fresh_reporting_gate", "template_gate", "visual_story_gate",
    ):
        if report.get(gate_name, {}).get("status") != "PASS": errors.append(f"{gate_name} failed")
    return errors


def validate_skill_package_release(root: Path, report: dict, qa: dict, proofs: dict[str, dict]) -> list[str]:
    """SKILL_PACKAGE_RELEASE: synthetic proofs prove skill function, never a customer result.

    The proof PDFs must be the ones an independent review passed against the fixed probe checklist, the QA record
    must be rebound to the live tree, customer mode must have refused every example-data case, and no proof may
    claim customer readiness or a customer semantic PASS.
    """
    errors: list[str] = []
    build = tree_digest(root)
    decision = report.get("skill_package_release") or {}
    if decision.get("status") != "PASS":
        errors.append("skill package release is not PASS")
    if decision.get("artifact_digest") != build:
        errors.append("skill package release not bound to the current build artifact digest")
    if qa.get("status") != PROOF_QA_PASS:
        errors.append("proof QA record is not PASS against the fixed checklist")
    if qa.get("artifact_digest") != build:
        errors.append("proof QA record not bound to the current build artifact digest")
    if qa.get("unadjudicated") != []:
        errors.append("proof QA record has unadjudicated review items")
    checklist = root / PROOF_CHECKLIST
    if not checklist.is_file() or qa.get("yardstick_sha256") != hashlib.sha256(checklist.read_bytes()).hexdigest():
        errors.append("proof QA yardstick differs from the fixed probe checklist")
    probes = re.findall(r"^\| ([A-E]\d) \|", checklist.read_text(encoding="utf-8"), re.M) if checklist.is_file() else []
    raw_rounds = (qa.get("independent_review") or {}).get("rounds") or []
    rounds = [r for r in raw_rounds if isinstance(r, dict) and type(r.get("round")) is int]
    numbers = [r["round"] for r in rounds]
    if not rounds or len(rounds) != len(raw_rounds) or len(numbers) != len(set(numbers)):
        errors.append("proof QA review rounds must carry unique integer round numbers")
    latest = max(rounds, key=lambda r: r["round"], default={})
    lines = latest.get("probe_lines") if isinstance(latest.get("probe_lines"), dict) else {}
    if type(latest.get("fail")) is not int or latest.get("fail") != 0 or latest.get("confirmed"):
        errors.append("latest independent proof review round has confirmed defects")
    owner = _owner_resolved_probes(checklist.read_text(encoding="utf-8")) if checklist.is_file() else set()
    if checklist.is_file() and latest.get("probe_rows_sha256") != probe_rows_sha256(checklist.read_text(encoding="utf-8")):
        errors.append("checklist probe rows differ from the rows the latest independent review used")
    owner &= {p for p in latest.get("owner_resolved") or [] if isinstance(p, str)}
    if not probes or sorted(lines) != sorted(probes) or not all(_probe_passed(k, v, owner) for k, v in lines.items()):
        errors.append("latest independent proof review did not pass every checklist probe")
    raw_cases, raw_refusals = qa.get("cases") or [], qa.get("customer_mode_refusals") or []
    cases = [c for c in raw_cases if isinstance(c, dict)]
    refusals = {r.get("case"): r for r in raw_refusals if isinstance(r, dict)}
    if not cases or len(cases) != len(raw_cases) or len(refusals) != len(raw_refusals):
        errors.append("proof QA record lists no cases or malformed case/refusal entries")
    names = [c.get("case") for c in cases]
    if len(names) != len(set(names)) or set(names) != RELEASE_CASES:
        errors.append("proof QA record does not cover exactly the nine release cases")
    for case in cases:
        name = case.get("case")
        if case.get("release_mode") != "proof":
            errors.append(f"proof case {name} was not built in proof mode")
        if not re.fullmatch(r"PASS( \(validate_pdf_visual_qa rc 0\))?", str(case.get("visual_qa", ""))):
            errors.append(f"proof case {name} visual QA is not PASS")
        if case.get("deliverable_status") != "CUSTOMER_RELEASE_BLOCKED":
            errors.append(f"proof case {name} must stay CUSTOMER_RELEASE_BLOCKED")
        refusal = refusals.get(name) or {}
        if refusal.get("blocked") is not True or refusal.get("pdf_written") is not False:
            errors.append(f"customer mode did not refuse proof case {name}")
    if any(r.get("blocked") is not True or r.get("pdf_written") is not False for r in refusals.values()):
        errors.append("customer mode did not refuse every example-data case")
    try:
        review_dir = reviewed_visual_qa_dir(root, qa)
    except ValueError as exc:
        errors.append(str(exc))
        review_dir = None
    for case in cases:
        name, pdf = case.get("case"), case.get("pdf_sha256")
        if not _is_sha256(pdf) or case.get("reviewed_pdf_sha256") != pdf:
            errors.append(f"proof case {name} PDF is not the PDF the independent review inspected")
        manifest = review_dir / f"{name}.visual-qa.json" if review_dir is not None and isinstance(name, str) else None
        try:
            inspected = json.loads(manifest.read_text(encoding="utf-8")) if manifest is not None and manifest.is_file() else {}
        except (OSError, ValueError):
            inspected = {}
        if inspected.get("inspection_status") != "PASS" or inspected.get("pdf_sha256") != pdf:
            errors.append(f"proof case {name} PDF is not the PDF of its review visual QA manifest")
    reviewed = {c.get("pdf_sha256") for c in cases if _is_sha256(c.get("pdf_sha256"))}
    for label, proof in proofs.items():
        if proof.get("release_mode") != "proof":
            errors.append(f"{label} proof was not built in proof mode")
        if proof.get("customer_release_ready") is not False:
            errors.append(f"{label} proof claims customer release readiness")
        if _claims_pass(proof.get("semantic_qa")):
            errors.append(f"{label} proof claims a customer semantic PASS on example data")
        if proof.get("visual_qa") != "PASS" or proof.get("proof_semantic_qa") != PROOF_SEMANTIC_PASS:
            errors.append(f"{label} proof is not visual PASS and PASS against the fixed checklist")
        if not _is_sha256(proof.get("pdf_sha256")) or proof.get("pdf_sha256") not in reviewed:
            errors.append(f"{label} proof PDF is not one of the reviewed proof PDFs")
    return errors


PACKAGE_FONT_POLICY = "PACKAGE_BUNDLED_MANIFEST_PINNED"
ANTI_SYCOPHANCY_THRESHOLD = 3

# Two release decisions (release-gate-policy.md): the skill package is proven on synthetic proofs; a customer report
# needs a real audit input. Proof QA is judged against the fixed probe checklist.
REAL_AUDIT_INPUT = "REAL_AUDIT_INPUT"
CUSTOMER_REPORT_BLOCKED = "BLOCKED_NO_REAL_AUDIT_INPUT"
PROOF_QA_PASS = "PROOF_QA_PASS_AGAINST_CHECKLIST_CUSTOMER_RELEASE_BLOCKED"
PROOF_SEMANTIC_PASS = "PASS_AGAINST_CHECKLIST"
PROOF_CHECKLIST = "docs/plans/2026-10-29-customer-pdf-qa-probe-checklist.md"
# The nine release cases scripts/run_customer_release_cases.py builds; a proof QA record must cover exactly these.
RELEASE_CASES = frozenset({"legacy-baseline", "legal-golden", "case-a-critical", "case-b-equal-rank-profile", "case-c-vc03-detail",
                           "active-positive", "proof-realistic", "proof-strategic", "proof-measurement-gateway"})
PROOF_QA_RECORD = re.compile(r"customer-pdf-qa-release-[0-9a-f]{7,40}\.json")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _claims_pass(value: object) -> bool:
    return isinstance(value, str) and value.strip().upper().startswith("PASS")


OWNER_RESOLVED = "AMBIGUOUS -> resolved PASS by owner clarification"


def probe_rows_sha256(checklist_text: str) -> str:
    """SHA-256 of the checklist's probe rows: an edit to a probe after the review changes it."""
    rows = [line for line in checklist_text.splitlines() if re.match(r"^\| [A-E]\d \|", line)]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _owner_resolved_probes(checklist_text: str) -> set[str]:
    """Probe IDs named on their own in the checklist's "Owner clarifications" table."""
    section = checklist_text.split("## Owner clarifications", 1)[1] if "## Owner clarifications" in checklist_text else ""
    section = re.split(r"^## ", section, maxsplit=1, flags=re.M)[0]
    return set(re.findall(r"^\| [^|]+ \| ([A-E]\d) \|", section, re.M))


def _probe_passed(probe: str, value: object, owner_resolved: set[str]) -> bool:
    """A probe passed, or was AMBIGUOUS and the checklist's owner-clarification table resolves exactly that probe."""
    return value == "PASS" or (value == OWNER_RESOLVED and probe in owner_resolved)


def _tree_file_hashes(root: Path) -> set[str]:
    return {hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


def reviewed_visual_qa_dir(root: Path, qa: dict) -> Path:
    """Folder of the per-case visual QA manifests written for the independent review, confined to reports/.

    They are JSON records, not cryptographic signatures; like every file under reports/ they bind hashes, not authorship.
    """
    rel = str(qa.get("reviewed_visual_qa_dir") or "")
    path = (root / rel).resolve()
    if not rel or path.parent != (root / "reports").resolve() or not path.is_dir():
        raise ValueError("proof QA record must name reviewed_visual_qa_dir as a folder under reports/")
    return path


def proof_qa_record_path(root: Path, report: dict) -> Path:
    """The proof QA record named in skill_package_release, confined to reports/customer-pdf-qa-release-<sha>.json."""
    rel = str((report.get("skill_package_release") or {}).get("proof_qa_record") or "")
    path = (root / rel).resolve()
    if path.parent != (root / "reports").resolve() or not PROOF_QA_RECORD.fullmatch(path.name):
        raise ValueError("skill_package_release.proof_qa_record must be reports/customer-pdf-qa-release-<sha>.json")
    return path


# Mirrors visualization_policy.CUSTOMER_FORBIDDEN_TEMPLATES for recorded proof evidence.
CUSTOMER_FORBIDDEN_PROOF_TEMPLATES = frozenset({"V01_OVERALL_SCORE", "V11_SEVERITY_DISTRIBUTION", "V12_AUDIT_COVERAGE"})


def validate_font_gate(root: Path, report: dict, fonts: dict) -> list[str]:
    """Font policy and strict-font evidence; re-derives the package font check live."""
    errors: list[str] = []
    strict = report.get("strict_customer_output_gate", {})
    brand = report.get("brand_rendering_gate", {})
    exact = bool(fonts.get("exact", {}).get("display") and fonts.get("exact", {}).get("data"))
    if exact:
        if strict.get("status") != "PASS": errors.append("exact fonts available but strict customer output gate is not PASS")
    else:
        if strict.get("status") != "BLOCKED_EXTERNAL_FONT": errors.append("missing exact fonts must block strict customer output")
        if strict.get("customer_release_ready") is not False: errors.append("missing exact fonts cannot be customer-release-ready")
    if brand.get("font_binary_policy") != PACKAGE_FONT_POLICY: errors.append("font binary policy must be the manifest-pinned package allowlist")
    if brand.get("strict_customer_mode_fail_closed") is not True: errors.append("strict customer font gate must fail closed")
    if fonts.get("package_policy") != PACKAGE_FONT_POLICY: errors.append("brand font capability report predates the package font policy")
    manifest = root / "assets/fonts/font-manifest.json"
    live_manifest = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None
    if (fonts.get("package_fonts") or {}).get("manifest_sha256") != live_manifest:
        errors.append("brand font capability report is stale against the font manifest")
    if brand.get("font_manifest_sha256") != live_manifest:
        errors.append("release brand gate is stale against the font manifest")
    try:
        policy = subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_no_font_binaries.py"), str(root)],
            text=True, capture_output=True, timeout=120,
        )
        if policy.returncode != 0:
            errors.append(f"package font allowlist live check failed: {(policy.stderr or policy.stdout).strip()}")
    except Exception as exc:
        errors.append(f"package font allowlist live check unavailable: {exc}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_release_gate.py <skill-dir>")
    root = Path(argv[1]).resolve()
    try:
        report = json.loads((root / "reports/release-gate-report.json").read_text(encoding="utf-8"))
        visual = json.loads((root / "reports/visual-reporting-eval-results.json").read_text(encoding="utf-8"))
        gallery = json.loads((root / "reports/visualization-gallery-eval-results.json").read_text(encoding="utf-8"))
        realistic = json.loads((root / "reports/realistic-presentation-qa.json").read_text(encoding="utf-8"))
        fonts = json.loads((root / "reports/brand-font-capability.json").read_text(encoding="utf-8"))
        gateway = json.loads((root / "reports/measurement-gateway-eval-results.json").read_text(encoding="utf-8"))
        protected = json.loads((root / "reports/measurement-platform-protected-baseline.json").read_text(encoding="utf-8"))
        third_party = json.loads((root / "reports/third-party-license-ledger.json").read_text(encoding="utf-8"))
        platform_proof = json.loads((root / "reports/measurement-platform-proof.json").read_text(encoding="utf-8"))
        strategic = json.loads((root / "reports/strategic-relevance-eval-results.json").read_text(encoding="utf-8"))
        strategic_proof = json.loads((root / "reports/strategic-relevance-proof.json").read_text(encoding="utf-8"))
        v321_preservation = json.loads((root / "reports/strategic-relevance-v321-preservation.json").read_text(encoding="utf-8"))
        quality_eval = json.loads((root / "reports/customer-presentation-quality-eval-results.json").read_text(encoding="utf-8"))
        quality_proof = json.loads((root / "reports/customer-presentation-quality-proof.json").read_text(encoding="utf-8"))
        active_core = json.loads((root / "reports/core-active-eval-results.json").read_text(encoding="utf-8"))
        active_mutations = json.loads((root / "reports/core-active-mutation-test-report.json").read_text(encoding="utf-8"))
        active_score = json.loads((root / "reports/score-reconciliation-report.json").read_text(encoding="utf-8"))
        active_analysis = json.loads((root / "reports/analysis-report-reconciliation.json").read_text(encoding="utf-8"))
        active_determinism = json.loads((root / "reports/core-active-determinism-report.json").read_text(encoding="utf-8"))
        active_render = json.loads((root / "reports/active-core-render-proof.json").read_text(encoding="utf-8"))
        legal_sources = json.loads((root / "reports/impressum-legal-source-validation.json").read_text(encoding="utf-8"))
        legal_evals = json.loads((root / "reports/impressum-compliance-eval-results.json").read_text(encoding="utf-8"))
        legal_customer = json.loads((root / "reports/legal-customer-projection-eval-results.json").read_text(encoding="utf-8"))
        paired = json.loads((root / "reports/paired-release-report.json").read_text(encoding="utf-8"))
        semantic = json.loads((root / "reports/semantic-customer-qa-eval-report.json").read_text(encoding="utf-8"))
        claims_eval = json.loads((root / "reports/evidence-bound-claims-eval-results.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid or missing release evidence: {exc}")

    errors: list[str] = []

    # Re-run the protected Measurement Platform guard on the exact candidate.
    # A stored PASS in release-gate-report.json is not sufficient because reports/
    # is excluded from the artifact digest and may otherwise become stale.
    try:
        protection = subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_measurement_platform_baseline.py"), str(root)],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if protection.returncode != 0:
            detail = (protection.stderr or protection.stdout).strip()
            errors.append(f"measurement platform preservation live check failed: {detail}")
    except Exception as exc:
        errors.append(f"measurement platform preservation live check unavailable: {exc}")
    # Same for the v3.2.1 preservation manifest: a stored PASS cannot vouch for code that changed afterwards.
    try:
        preservation = subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_strategic_relevance_v321_preservation.py"), str(root)],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if preservation.returncode != 0:
            detail = (preservation.stderr or preservation.stdout).strip()
            errors.append(f"v3.2.1 preservation live check failed: {detail}")
    except Exception as exc:
        errors.append(f"v3.2.1 preservation live check unavailable: {exc}")
    # Evidence-bound customer claims: the stored eval must be PASS for this tree, and the suite is re-run live
    # (a skipped case is NOT RUN, which the runner already reports as FAIL).
    try:
        with tempfile.TemporaryDirectory(prefix="pxk-claims-") as td:
            live_out = Path(td) / "evidence-bound-claims-eval-results.json"
            live_claims = subprocess.run(
                [sys.executable, "-B", str(root / "scripts" / "run_evidence_bound_claim_evals.py"), str(root), "--json-out", str(live_out)],
                text=True, capture_output=True, timeout=900,
            )
            live_doc = json.loads(live_out.read_text(encoding="utf-8")) if live_out.is_file() else {}
        if live_claims.returncode != 0 or live_doc.get("status") != "PASS":
            errors.append(f"evidence-bound claims live eval failed: {(live_claims.stdout or live_claims.stderr).strip()[:300]}")
    except Exception as exc:
        errors.append(f"evidence-bound claims live eval unavailable: {exc}")
    if claims_eval.get("status") != "PASS" or claims_eval.get("skipped"):
        errors.append("evidence-bound claims eval evidence is not PASS")
    try:
        if claims_eval.get("artifact_digest") != tree_digest(root):
            errors.append("evidence-bound claims eval evidence is stale (STALE_ARTIFACT_DIGEST)")
    except Exception as exc:
        errors.append(f"evidence-bound claims digest check unavailable: {exc}")
    errors.extend(validate_gate_statuses(report))

    if legal_sources.get("status") != "PASS": errors.append("impressum legal source validation failed")
    if legal_evals.get("status") != "PASS" or int(legal_evals.get("pass_count", 0)) != int(legal_evals.get("case_count", -1)): errors.append("impressum compliance evals failed")
    required_legal_customer = {"bo_feng_lin_mandatory_projection", "core_score_coverage_delta_zero", "mandatory_legal_risk_rank1_cover_roadmap_closing", "mandatory_legal_risk_visible_in_rendered_pdf", "omission_fails_closed", "anti_overclaim_preserved"}
    if legal_customer.get("status") != "PASS" or not required_legal_customer.issubset(set(legal_customer.get("checks") or [])):
        errors.append("impressum customer-risk projection evals failed")
    if legal_customer.get("pixelkiez_score_impact") != "NONE_DIRECT": errors.append("legal customer projection changed score firewall")
    if report.get("pixelkiez_score_impact") != "NONE_DIRECT": errors.append("legal score firewall missing")

    # Active Core Migration is additive and non-compensatory.
    if active_core.get("status") != "PASS" or active_core.get("suite") != "FULL_48_ACTIVE":
        errors.append("active core eval failed")
    for key in ("total_registry_metrics", "execution_ready", "evidence_ready", "score_admitted", "report_reconciled"):
        if active_core.get(key) != 48:
            errors.append(f"active core {key} must equal 48")
    if "synthetic evidence" not in str(active_core.get("fixture_boundary", "")).lower():
        errors.append("active core fixture boundary missing")
    if active_mutations.get("status") != "PASS" or int(active_mutations.get("detected", 0)) < 15:
        errors.append("active core mutation gate incomplete")
    if active_score.get("status") != "PASS" or active_score.get("registry_weights_unchanged") is not True or active_score.get("compute_score_changed") is not False:
        errors.append("active core score integrity failed")
    if active_score.get("fixture_only") is not True:
        errors.append("active score proof must remain fixture-only")
    if active_analysis.get("status") != "PASS" or active_analysis.get("metric_count") != 48 or active_analysis.get("weighted_contributions") != "RECONCILED":
        errors.append("active analysis reconciliation failed")
    if active_determinism.get("status") != "PASS" or active_determinism.get("semantic_digest") != active_determinism.get("shuffled_semantic_digest"):
        errors.append("active core determinism failed")
    if active_render.get("status") != "PASS" or active_render.get("renderer") != "WEASYPRINT":
        errors.append("active core rendered customer proof failed")
    if not 8 <= int(active_render.get("page_count", 0)) <= 12 or int(active_render.get("embedded_visual_count", 0)) < 4:
        errors.append("active core rendered customer proof incomplete")
    needed_active_validators = {"validate_pdf_output", "validate_presentation_brand", "validate_customer_business_language", "validate_customer_output_guardrails"}
    if not needed_active_validators.issubset(set(active_render.get("validators") or [])):
        errors.append("active core render validator coverage incomplete")
    if active_render.get("fixture_only") is not True:
        errors.append("active core render proof must remain fixture-only")

    exact = bool(fonts.get("exact", {}).get("display") and fonts.get("exact", {}).get("data"))
    errors.extend(validate_font_gate(root, report, fonts))

    if visual.get("status") != "PASS" or visual.get("metric_count") != 48: errors.append("visual/reporting architecture eval incomplete")
    if visual.get("mandatory_product_outputs") != ["analysis_report.json", "analysis_report.md", "customer_presentation.pdf"]: errors.append("mandatory output contract drift")
    if not 5 <= int(visual.get("selected_visual_count", 0)) <= 7: errors.append("visual architecture eval must select 5-7 visuals")
    if visual.get("renderer") != "WEASYPRINT": errors.append("WeasyPrint was not validated as customer renderer")
    if visual.get("benchmark_without_context") != "BLOCKED" or visual.get("ranking_without_context") != "BLOCKED": errors.append("fake benchmark/ranking negative controls failed")
    if visual.get("unsafe_svg") != "REJECTED": errors.append("unsafe SVG negative control failed")

    if gallery.get("status") != "PASS" or gallery.get("vega_lite_templates") != 14 or gallery.get("rendered_count") != 15:
        errors.append("approved visualization gallery incomplete")
    if realistic.get("status") != "PASS" or not 8 <= int(realistic.get("page_count", 0)) <= 12 or not 4 <= int(realistic.get("selected_visual_count", 0)) <= 7:
        errors.append("realistic rendered presentation QA incomplete")
    # Proof QA (visual + fixed checklist) and the customer-semantic boundary are checked in validate_skill_package_release.
    if realistic.get("internal_metric_count") != 48: errors.append("realistic internal report is not complete")
    if realistic.get("customer_release_ready") is not False and not exact: errors.append("realistic proof incorrectly claims exact-font customer release")
    for label, proof in (("realistic", realistic), ("strategic", strategic_proof), ("measurement platform", platform_proof)):
        if set(proof.get("selected_template_ids") or []) & CUSTOMER_FORBIDDEN_PROOF_TEMPLATES:
            errors.append(f"{label} customer proof selected forbidden score/finding-count/coverage visual")


    if gateway.get("status") != "PASS" or gateway.get("core_metric_count") != 48:
        errors.append("measurement gateway integration eval incomplete")
    if gateway.get("scoring_policy") != "NON_SCORING_ENRICHMENT":
        errors.append("measurement gateway must remain non-scoring enrichment")
    if protected.get("baseline_tree_digest") != report.get("measurement_platform_baseline_digest"):
        errors.append("measurement platform baseline digest mismatch")
    protected_files = protected.get("protected_files")
    if not isinstance(protected_files, list) or len(protected_files) < 40:
        errors.append("protected baseline manifest incomplete")
    repos = third_party.get("repositories")
    if not isinstance(repos, list) or len(repos) != 4 or any(item.get("source_code_copied") is not False for item in repos if isinstance(item, dict)):
        errors.append("third-party no-copy gate failed")
    if platform_proof.get("status") != "PASS":
        errors.append("measurement platform proof status failed")
    # Enriched synthetic fixture: six admissible visuals since the finding-count visual is internal-only (SEM-003).
    if platform_proof.get("renderer") != "WEASYPRINT" or platform_proof.get("page_count") != 11 or platform_proof.get("selected_visual_count") != 6:
        errors.append("measurement platform rendered proof incomplete")
    if platform_proof.get("pdf_output") != "PASS" or platform_proof.get("pdf_brand") != "PASS" or platform_proof.get("customer_language") != "PASS":
        errors.append("measurement platform PDF proof validators failed")
    if platform_proof.get("protected_customer_closing") is not True or platform_proof.get("protected_visual_catalog") is not True:
        errors.append("protected presentation invariants not preserved")
    if strategic.get("status") != "PASS" or strategic.get("internal_metric_inventory") != 48:
        errors.append("strategic relevance regression incomplete")
    required_strategic = {"partial_score_customer_bewertungsstand", "process_finding_rejected", "not_assessed_not_customer_problem", "legal_sidecar_route_customer_eligible", "customer_visual_score_coverage_guard", "internal_transparency_preserved"}
    if not required_strategic.issubset(set(strategic.get("checks") or [])):
        errors.append("strategic relevance required checks incomplete")
    if quality_eval.get("status") != "PASS":
        errors.append("customer presentation quality regression failed")
    if quality_proof.get("status") != "PASS" or quality_proof.get("final_state", {}).get("quality_status") != "PROOF_PASS_CUSTOMER_BLOCKED":
        errors.append("customer presentation quality rendered proof failed")
    if quality_proof.get("initial_state", {}).get("quality_status") != "PENDING_QA" or quality_proof.get("initial_state", {}).get("delivery_allowed") is not False:
        errors.append("quality proof does not demonstrate fail-closed PENDING_QA draft state")
    if quality_proof.get("observed_repair_loop", {}).get("rerender_required") is not True or quality_proof.get("observed_repair_loop", {}).get("all_pages_reinspected_after_repair") is not True:
        errors.append("quality proof does not demonstrate repair/rerender/reinspection loop")
    required_quality = {"partial_score_as_bewertungsstand", "ordinal_priority_no_fake_magnitude", "privacy_overclaim_rejected", "closing_action_fragment_rejected", "four_lever_business_impact_rendered"}
    if not required_quality.issubset(set(quality_eval.get("checks") or [])):
        errors.append("customer presentation quality required checks incomplete")
    if report.get("visual_story_gate", {}).get("customer_score_policy") != "FULL_SCORE_OR_PARTIAL_BEWERTUNGSSTAND":
        errors.append("customer score projection policy not reconciled")
    if strategic_proof.get("status") != "PASS" or strategic_proof.get("guardrails") != "PASS":
        errors.append("strategic customer proof failed")
    if strategic_proof.get("top_lever_count") != 4 or not 4 <= int(strategic_proof.get("selected_visual_count", 0)) <= 7:
        errors.append("strategic proof story contract failed")
    if strategic_proof.get("internal_metric_count") != 48:
        errors.append("strategic proof internal metric inventory incomplete")
    if int(strategic_proof.get("measurement_enrichment_metric_count", 0)) < 1:
        errors.append("combined strategic/measurement proof missing enrichment")
    if v321_preservation.get("status") != "PASS" or v321_preservation.get("baseline_tree_digest") != "f9663c8c616f1c6ea1be95098eb6c27065f2018e4f8fe47499059cca93e637f6":
        errors.append("v3.2.1 merge preservation evidence failed")
    if v321_preservation.get("deleted_files"):
        errors.append("v3.2.1 merge unexpectedly deletes baseline files")
    live = report.get("measurement_gateway_live_gate", {})
    if live.get("status") not in {"PASS", "NOT_ASSESSED_NON_BLOCKING"}:
        errors.append("measurement gateway live gate status invalid")
    if live.get("package_blocking") is not False:
        errors.append("optional live gateway verification must be explicitly non-package-blocking")

    proof_pdfs: set[str] = set()
    try:
        proof_qa = json.loads(proof_qa_record_path(root, report).read_text(encoding="utf-8"))
        proof_pdfs = {c.get("pdf_sha256") for c in proof_qa.get("cases") or [] if isinstance(c, dict)}
        proofs = {"realistic": realistic, "strategic": strategic_proof, "quality": quality_proof.get("final_state") or {},
                  "active core render": active_render, "measurement platform": platform_proof}
        errors.extend(validate_skill_package_release(root, report, proof_qa, proofs))
    except Exception as exc:
        errors.append(f"skill package proof evidence unavailable: {exc}")
    try:
        errors.extend(validate_reports(root, report, paired, semantic, proof_pdfs))
    except Exception as exc:
        errors.append(f"cross-skill/semantic evidence unavailable: {exc}")

    try:
        current = tree_digest(root)
        if report.get("artifact_digest") != current: errors.append(f"release report artifact digest stale: {report.get('artifact_digest')} != {current}")
    except Exception as exc:
        errors.append(f"artifact digest unavailable: {exc}")

    if errors:
        return fail("; ".join(errors))
    print("PASS: release gate visual/reporting architecture + customer quality gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
