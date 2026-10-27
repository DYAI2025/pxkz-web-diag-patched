# Branch-aware customer prioritization (v1, non-scoring)

## Purpose and decision boundary

Pixelkiez selects the same four evidence-supported strategic levers for its concise customer presentation. The goal is to identify concrete business gaps, evidence-backed **technical and visual** improvement opportunities, and selectively illustrative diagnostic details. A small detail such as an absent favicon can show thoroughness if observed, but it is not proof of generally poor maintenance, nor a guaranteed cause of lost revenue.

**Business priority is not website quality.** The canonical 48 Core metrics, category and metric weights, score anchors, score admission and `compute_score.py` remain untouched. No branch profile can modify any score, measured website state, coverage, legal assessment or provider result. The branch policy affects customer **selection order only**, not factual admission or copy truth.

## Authority hierarchy

1. **Safety, assessed evidence and mandatory visibility** — validated legal-sidecar requirements, especially `MANDATORY_CRITICAL`, cannot be displaced. `not_assessed`, errors, internally process-only items and unsupported findings cannot become customer findings.
2. **Verified approved sector profile** — only an applicable `APPROVED` profile in a versioned registry with date range, source reference, product-policy/market-evidence basis and responsible approver can govern relative business priorities. An *internal Pixelkiez product-policy profile* is a business heuristic, **not** proof of the industry's objective average. A market-research basis requires actually inspected, current population and measurement evidence before comparative claims.
3. **Owner-confirmed business goal** — an exact goal-specific weight map in that same approved sector profile can be used when owner confirmation is supplied through a trusted operator context. The model must not derive a goal from generic website wording and pretend the owner confirmed it.
4. **Current audited facts** — within the established severity classes, approved industry and goal weights reorder evidence-admitted findings by category. Category diversity remains a selection objective, and no lower-severity finding jumps ahead of a supported higher-severity one. Do not convert severity into a new weighted overall numeric score.
5. **No applicable profile** — retain the existing deterministic, confidence- and category-diversity-based selection unchanged. Report `LEGACY_PRIORITY` internally; do not invent percentages, peer medians or a generic sector benchmark.

These controls are non-compensatory. No customer sales objective or visually impressive opportunity may override evidence/eligibility/safety.

## Data and runtime contract

- `assets/branch-priority-profiles.v1.json`: bundled empty, truthful catalog. There are **no registered verified sector weights** in this patch. Adding real weights is a separate evidence-and-approval action. The six `category_weights` keys mirror the existing six categories; each approved map sums to 100. The numbers are **relative presentation policy weights**, not contribution to the Pixelkiez Score.
- `schemas/branch-priority.schema.json`: validates a precise `industry_id`, `business_model_id`, identity evidence source, date, optionally owner-confirmed goal, and optional audited finding roles. Values are fixed IDs, never fuzzy LLM-derived similarity.
- `scripts/branch_priority.py`: validates exact applicability, approval state, temporal validity, weight sums, duplicate identity, role-to-finding/evidence links. Conflicts or malformed inputs block an explicitly requested contextual build.
- `scripts/client_story.py`: existing default selector unchanged when no approved profile is active. Approved weights change ordering *within* the existing critical/high/medium/low severity bands only. Legal mandatory priority remains top.
- `scripts/build_client_report_model.py`: opt-in `--priority-context` and `--priority-catalog` (external catalog additionally requires an exact `--priority-catalog-sha256`), optional `--priority-decision-out` for internal provenance. Context and registry are operator-controlled runtime inputs; never loaded from arbitrary web page metadata.
- `scripts/build_audit_deliverables.py`: same opt-in flags; saves `prioritization-decision.json` internally when context was supplied. The customer HTML/PDF does not contain profile weights, selection provenance or approval data.

No industry context or registry is required to run the existing standalone skill. No API/connector is implicitly authorized. PXAPI remains a future canonical measurement source where available and verified; business prioritization is a separate presentation decision.

### Roles for technical, visual and illustrative value

Optional `roles` are labels on **already eligible findings**, not new measurements or scores. Three controlled roles are allowed: `BUSINESS_GAP`, `PREMIUM_OPPORTUNITY`, `PRECISION_DEMONSTRATION`, and three axes `TECHNICAL`, `VISUAL`, `BOTH`. Each role requires exact existing finding and evidence IDs plus a plausible, explicitly stated business mechanism. Within equally weighted category/severity findings, `PREMIUM_OPPORTUNITY` and `PRECISION_DEMONSTRATION` can break ties; they cannot displace a legally required, critical or high-severity item.

**Premium is a proposal, not a comparative claim.** In customer language prefer “gezielte Verbesserung”, “hochwertigerer Auftritt” or “Differenzierungspotenzial” when justified. “Über dem Branchendurchschnitt”, “Premiumstandard erreicht” or specific conversion/revenue/lead deltas require actual matched comparative or outcome evidence. Not having a visible favicon is not proof of a poor brand or bad business.

## Proof and regression

1. Run `python -m unittest discover -s tests -p 'test_branch_priority.py' -v`.
2. Run old `run_strategic_relevance_evals.py`, `run_score_gate_evals.py`, `run_full_48_active_evals.py` and the VibeCheck03 tests.
3. Negative cases: unknown or expired profile, conflicting approvals, wrong-page identity, missing owner goal, invalid weight sums, fake premium evidence, duplicate roles, customer PDF metadata leakage and simulated HTML instruction injection cannot grant authority.
4. Compare old/new selection on the same canonical input **without optional context**; required exact match. With approved profile, only selection order may change, and core score and legal priorities must not.
5. Compare complete internal reports, PDF, mandatory four levers, chart counts, brand, legal override, ElevenLabs compatibility, renderer QA and exact final digest prior to release.

## Known limitations / rollout

- Current bundled catalog has zero approved industry profiles. The contextual code path is supported by synthetic fixtures, **not** evidence that real industry weighting has been calibrated or improves outcomes.
- Website source evidence can support industry identification only if bound to actual report source IDs. Owner confirmation must be gathered through an operator-authorized trusted channel; mere presence of a JSON field is not independent identity verification.
- The earlier VibeCheck03 patch still has separate open issues: safe live browser/404 acquisition, non-core evidence-to-customer admission, full PDF regression and independent evaluator receipt. This additive priority patch does **not** silently declare those complete.
- A prior report remains valid as a factual audit, but changing customer selection requires fresh customer-model, PDF and semantic QA on the exact candidate digest.
