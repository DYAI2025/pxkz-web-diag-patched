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
- font binaries absent from package;
- exact-font customer mode fail-closed;
- visual/semantic QA creation remains fail-closed;
- current visual-source/brand/template digests in the release report.

The Skill may be packaged when it correctly blocks a customer release without exact fonts. It may not claim that a proof-mode PDF using fallback fonts is fully brand-identical or customer-release-ready.

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
