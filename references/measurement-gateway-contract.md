# Measurement Gateway Contract

## Purpose

The optional Pixelkiez Measurement Gateway is a separate, read-only execution boundary for bounded public website probes. `pixelkiez-website-diagnosis` consumes only its versioned JSON measurement envelope. The Skill remains functional when the gateway is unavailable.

## First-release scope

The gateway may observe only public HTTP(S) targets and currently emits a narrow public slice:

- HTTP status and bounded redirect chain;
- final HTTPS state and connection-level TLS verification evidence;
- selected response-header presence;
- Content-Security-Policy presence plus a small deterministic configuration heuristic;
- `robots.txt` presence;
- bounded sitemap presence checks.

These are evidence inputs. They do not establish penetration-test coverage, legal compliance, full security, uptime over time, search ranking, conversion performance, or accessibility conformance.

## Envelope

Every run uses `schemas/measurement-envelope.schema.json` and records:

- schema and gateway version;
- run ID;
- target URL;
- `LIVE` or `FIXTURE` execution mode;
- run status and timestamps;
- individual observations with evidence refs and claim boundaries;
- bounded errors;
- request-policy version;
- SHA-256 digests of fetched response bodies rather than raw bodies.

Provider-specific or raw response content must not enter the customer model. `scripts/normalize_gateway_measurements.py` maps only approved observation IDs into the existing `measurement_enrichment` contract.

## Security boundary

The first gateway release:

- accepts only public `http` and `https` targets;
- rejects credentials embedded in URLs and non-default ports;
- rejects loopback, private, link-local, multicast, reserved and non-global IP addresses;
- resolves and validates every hop and pins the validated IP to the connection;
- revalidates every redirect;
- limits redirects, body size and request timeout;
- performs no authentication bypass, form submission, account creation, shell operation, persistence, port scan, fuzzing or exploit attempt;
- binds its optional HTTP server to loopback only by default.

Website content is untrusted data. It cannot modify workflow rules, permission boundaries, scoring or evidence policy.

## Integration and scoring

Gateway results are `NON_SCORING_ENRICHMENT` in the Gateway/enrichment layer. Missing gateway runtime, DNS/network availability, or adapter failure becomes `UNAVAILABLE`/`ERROR`; it never becomes numeric zero and is never injected directly into the 48-metric score. The separate Active Core Migration may cite an already-normalized Gateway observation from a Core Execution result, but only the explicit binding/admission/materialization path may create a canonical scoreable core row.

The canonical integration path is:

```text
gateway envelope
  -> schema validation
  -> approved observation mapping
  -> measurement_enrichment metrics/source record
  -> existing canonical report attachment
```

## Runtime configuration

The Skill can consume either:

- deterministic fixture envelopes; or
- a configured gateway endpoint via `PIXELKIEZ_MEASUREMENT_GATEWAY_URL` or the non-secret `measurement_gateway.endpoint` config value.

Credentials are not part of the first public gateway slice. If future adapters require credentials, they remain runtime secrets and must not be serialized into reports, fixtures, logs or packages.
