# Impressum Compliance Method

## Purpose

Add a non-core legal sidecar for provider-identification risk. The canonical Pixelkiez 48-metric score remains independent. `pixelkiez_score_impact = NONE_DIRECT`.

## Mandatory sequence

Website evidence -> jurisdiction gate -> business/context gate -> legal regime -> applicability -> evidence admission -> defect -> severity -> internal ILES/exposure -> review or supported finding -> schema-valid finding projection -> unchanged core scoring.

## Evidence boundary

Legal rule evidence and website fact evidence are separate. `ABSENT` requires a completed discovery scope. Fetch/tool failure produces `NOT_ASSESSED` or `POSSIBLE_LEGAL_REVIEW`, never absence. `INCORRECT` requires authoritative counterevidence; unresolved cross-source mismatch stays `CONTRADICTORY`. Weak signals such as `.de`, language, WHOIS/RDAP, return address or payment logos cannot alone confirm establishment or operator identity.

## Applicability and ILES

Only `APPLICABLE` plus current primary rule evidence plus measured/observed E1-E4 evidence plus supported defect plus no unresolved conflict admits a full dimension weight. `LIKELY_APPLICABLE`, `CONDITIONAL`, `UNKNOWN`, `inferred_risk`, E5-E8 and unresolved conflict always score zero. IMP-10 and IMP-11 are modifiers and never add a second dimension weight.

## Overrides

`ILES_CRITICAL_OVERRIDE` requires applicable regime, current primary rule and strong admitted evidence for operator identity, geographic address, total provider-identity absence, or B2C pre-contract counterparty identity. `AUDIT_PRIORITY_CRITICAL` may surface strongly observed operator opacity while jurisdiction remains unresolved, but then applicability is `UNKNOWN`, ILES is zero and the claim state is `POSSIBLE_LEGAL_REVIEW`.

## Customer semantics

Permitted wording is bounded to review/action language such as “Möglicher rechtlicher Handlungsbedarf” or “Dringender rechtlicher Prüfbedarf”. No certification, definitive unlawfulness claim, automatic GDPR inference, or expected fine prediction is permitted. Statutory maxima are internal enforcement context only unless an explicitly authorized reporting context binds the current primary source.

## Customer-risk surfacing

Legal certainty and customer visibility are separate axes. `legal_customer_projection.py` resolves validated sidecar evidence into `MANDATORY_CRITICAL | MANDATORY_HIGH | ELIGIBLE | INTERNAL_ONLY`. `AUDIT_PRIORITY_CRITICAL` remains `POSSIBLE_LEGAL_REVIEW` when jurisdiction is unresolved, but it is still `MANDATORY_CRITICAL` for customer visibility. A mandatory provider-identity risk must be consolidated into one finding, rank first among the four levers, appear on the cover, in `roadmap.now`, and in the closing action list. This routing never changes Core score, coverage, metric weights, or ILES.

Customer wording must name the observed defect directly (for example missing or unclear operator identity/address) and recommend qualified legal review. Tax-identification issues may additionally recommend tax review. Unresolved jurisdiction must never be rewritten as a definitive violation.
