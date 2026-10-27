# Build Pipeline Ledger

The package uses `scripts/pipeline_ledger.py` and `reports/build-events.jsonl` to record a hash-chained build trace when deterministic file execution is available.

## What it proves

The ledger proves only process state:

- required stages were recorded in order;
- post-freeze gates refer to the same build-controlled artifact digest;
- the trace has no sequence/hash break;
- packaging was authorized for that frozen digest.

It does **not** prove that external sources are true, that a customer website is healthy, that runtime tools behaved correctly, or that the score is externally standardized.

## Build-controlled digest

The digest includes skill files except `reports/`, caches, `.git`, and `dist/`. Reports are excluded so release/evaluation/validation evidence can be written after the draft is frozen without self-invalidating the digest.

## Required sequence

1. `INTAKE_COMPLETED`
2. `RESEARCH_COMPLETED`
3. `CAPABILITY_DECISION_SKIPPED`
4. `ARCHITECTURE_GATE_PASSED`
5. `DRAFT_FROZEN`
6. `RELEASE_GATE_PASSED`
7. `EVALUATOR_PASSED`
8. `VALIDATION_PASSED`
9. `PACKAGE_AUTHORIZED`

The last five events carry the same artifact digest. Any material change outside `reports/` requires a new freeze and a new ledger run.

## Batch-contract release evidence

For the v2.1 batch update, validation on the frozen artifact must include the shared-contract validator, 17 batch acceptance evals and the extended fixture run in addition to the existing score/PDF/schema/security/core-parity gates. The hash ledger proves that these gate claims refer to the same build-controlled artifact digest; it does not prove the sibling Voice Architect task or any ElevenLabs/live-call runtime behavior.
