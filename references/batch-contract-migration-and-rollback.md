# Batch contract migration and rollback

- v1: 82 fields, explicit legacy mode.
- v1.1: 83 fields, adds optional `customer_email`.
- v1.2: 96 fields, appends the 13 current-agent Dynamic Variable names observed on 2026-08-28.
- v1.3: 96 fields, default. It preserves the exact v1.2 header and introduces the five-class readiness model.

## v1.3 migration rule

The migration is semantic, not structural: no CSV field is added, removed, renamed, reordered, or case-changed from v1.2. `customer_email` becomes explicitly `OPTIONAL`; unknown prospect/contact data may be compiler-defaulted where the current agent requires a non-empty variable; Campaign/CRM/Compliance/Meeting authority values move to `PRODUCTION_GATE_ONLY` readiness semantics.

Because v1.2 and v1.3 have identical headers, auto-detection resolves a 96-field row to v1.3. Historical v1.2 validation must use `--contract-version v1.2`.

## Rollback

Rollback is explicit: select v1.2, v1.1 or v1, or revert the complete skill package. Never relabel a v1.3 sidecar/digest as v1.2.

## Cross-skill coupling

The v1.3 metadata/digest is release-coupled only when a downstream Voice Architect also adopts v1.3 digest validation. The 96-column wire header remains v1.2-compatible, but exact digest/version parity must not be claimed until the consumer carries the same v1.3 contract bytes.
