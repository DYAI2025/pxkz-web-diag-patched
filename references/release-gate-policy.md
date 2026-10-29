# Release Gate Policy

Packaging requires all of the following:

- coherent smallest scope and progressive disclosure;
- current sources or correct `SOURCE_NEEDED` markings;
- no unsupported quantitative, legal, security, ranking, revenue, or future claim;
- anti-sycophancy score below 3;
- confirmation, overconfidence, tool, authority, cultural, and user-thesis-laundering bias reviewed;
- `blocked_claims` empty;
- validators and the synthetic PDF fixture pass;
- the rendered PDF is visually inspected;
- the archive contains exactly one skill folder.

If any condition fails, revise or set the release status to `BLOCKED`. Never manufacture a pass.


## Visualization/reporting release gate

The Skill package release requires:

- visualization template gallery PASS 15/15;
- full reporting-bundle E2E PASS;
- complete internal JSON/Markdown metric reports;
- WeasyPrint default renderer;
- only manifest-pinned, verified brand fonts and their licences in the package (`validate_no_font_binaries.py`, re-run live by the release gate and by `package_skill.py`); no fonts in customer deliverables;
- exact-font customer mode fail-closed;
- visual/semantic QA creation remains fail-closed;
- current visual-source/brand/template digests in the release report.

The Skill may be packaged when it correctly blocks a customer release without exact fonts. It may not claim that a proof-mode PDF using fallback fonts is fully brand-identical or customer-release-ready.

## Two release decisions

`validate_release_gate.py` decides two things separately and never lets one stand in for the other:

- **`SKILL_PACKAGE_RELEASE`** (`skill_package_release` in `reports/release-gate-report.json`): may `skill.zip` be built and installed? Synthetic proofs prove skill function. It needs a proof QA record `reports/customer-pdf-qa-release-<commit>.json` rebound to the live tree digest whose latest independent review round passed every probe of the fixed checklist (`docs/plans/2026-10-29-customer-pdf-qa-probe-checklist.md`, bound by its SHA-256), every case's PDF hash equal to the one the review inspected and to the hash in that case's visual QA manifest written for the review (`reviewed_visual_qa_dir` under `reports/`; these manifests are JSON records, not cryptographic signatures, and like every file under `reports/` they lie outside the tree digest), every proof report citing one of those PDF hashes, customer mode refusing each of the nine release cases without writing a PDF, and no proof claiming customer readiness or a customer semantic PASS. The latest review round is the highest of unique integer round numbers. A probe counts as passed when it reads `PASS`, or `AMBIGUOUS -> resolved PASS by owner clarification` with a row for exactly that probe in the checklist's owner-clarifications table. The gate compares recorded hashes; it does not re-render. That the current tree still produces the reviewed PDFs is shown when the record is rebound, by rebuilding the release cases from the frozen candidate and comparing every PDF and page raster byte for byte. Proof records carry `proof_semantic_qa: PASS_AGAINST_CHECKLIST`; their `semantic_qa` stays the customer semantic result, which example data cannot pass.
- **`CUSTOMER_REPORT_RELEASE`** (`customer_report_release`): is a customer report built from a real audit validated? `PASS` needs customer semantic QA on a real audit input built in customer mode (`release_mode: customer`, `data_class: REAL_AUDIT_INPUT`) bound to the live semantic bundle and tree, an `audit_input_sha256` that is no file of the skill tree, a `pdf_sha256` that is none of the proof PDFs, and no fixture provenance. `data_class` is a recorded label: the gate cannot prove that an external input is real beyond these checks, and customer mode refusing example data (`SYNTHETIC_EVIDENCE_IN_CUSTOMER_OUTPUT`) is the build-time guard. Without a real audit the state is `BLOCKED_NO_REAL_AUDIT_INPUT`, declared `package_blocking: false` and `customer_release_ready: false`. A semantic PASS (any `PASS…` spelling) on proof or example data is rejected in either state, and while the customer report is blocked no gate in the release report may claim `customer_release_ready: true`.

The pipeline ledger (`reports/build-events.jsonl`, `validate_pipeline_ledger.py`) records the release gate passing, so the release gate cannot require it; `package_skill.py` runs both and refuses to build `skill.zip` unless both pass.

A package release therefore never says anything about a customer report. Each customer deliverable still needs its own `validate_deliverable_bundle.py --require-customer-release-ready`.

## Customer Presentation Quality Gate

Final customer-presentation delivery is non-compensatory. `customer-presentation-quality-report.json` must be `PASS` for the exact final PDF/model/scored-report digest set. `PENDING_QA` is a valid build state but blocks final-delivery claims. Exact fonts remain a separate strict customer-release condition.


## Active Core Migration Gate

The Active Core Migration adds a non-compensatory gate; it does not replace or weaken any existing reporting, customer-presentation, batch, gateway or protected-baseline gate.

Packaging requires all of the following on the frozen candidate digest:

- exact 48/48 active binding equality to `assets/measurement-registry.json`;
- protected registry weights, category weights, score anchors and `scripts/compute_score.py` byte-identical to the frozen pre-migration baseline;
- 48 execution results in the golden contract fixture and 48/48 Score Admission;
- explicit rejection of unavailable/error/conflict/raw-provider/wrong-target/weight-drift/unknown-metric cases;
- required mutation suite PASS;
- independent golden score recomputation equals the existing `compute_score.py` result;
- deterministic semantic digest and score result under input reordering;
- internal `analysis_report` weight/contribution reconciliation PASS;
- a fresh fixture-based WeasyPrint render through the active core path passes PDF, brand, customer-language and customer-output leakage validators;
- the golden fixture remains labeled fixture-only and may not be cited as live website measurement proof.

A concrete website audit can still have fewer than 48 score-admitted metrics. Missing real evidence must reduce coverage; it is not a package regression.
