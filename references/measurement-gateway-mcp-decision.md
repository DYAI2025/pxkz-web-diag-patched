# Measurement Gateway MCP Decision

Status: `DEFERRED_NOT_REQUIRED_FOR_FIRST_RELEASE`.

The first Measurement Platform patch uses a versioned JSON envelope and an optional loopback HTTP interface. MCP is not a required dependency because it would add another transport and permission surface before the domain contract is stable.

A future MCP wrapper may be added only if:

- the measurement domain and schemas remain unchanged;
- tools are task-level, read-only and non-destructive;
- no arbitrary fetch, shell, database or credential tool is exposed;
- authentication, tenant isolation, rate limits and error contracts are explicit;
- a normal API/local fallback remains available.
