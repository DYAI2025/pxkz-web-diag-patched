# Owner Analytics Adapter Contract

Owner analytics is read-only, permission-bound evidence and is separate from public website probing.

Any future provider maps to `schemas/owner-analytics.schema.json` and must preserve:

- audited target/property;
- explicit owner authorization state;
- provider and date range;
- tracked metric/event identity;
- instrumentation coverage (`TRACKED`, `PARTIAL`, `NOT_INSTRUMENTED`, `UNKNOWN`);
- the boundary that events never recorded cannot be reconstructed as historical fact.

Open Web Analytics can be evaluated as an opt-in self-hosted provider after separate operational, privacy and licensing review. Existing GA4/Search Console adapters remain valid and unchanged.
