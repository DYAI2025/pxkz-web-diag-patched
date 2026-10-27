# Continuous Monitoring Adapter Contract

Continuous monitoring is separate from one-shot website diagnosis. A successful request at audit time must never be converted into an uptime percentage.

Any future provider maps to `schemas/availability-monitoring.schema.json` and must preserve:

- monitored target;
- observation period and sampling interval;
- individual samples or provider-supported aggregates;
- incident/maintenance boundaries where available;
- provider identity and measurement state;
- `CONTINUOUS_MONITORING` evidence class.

Provider absence is `NOT_CONFIGURED` or `UNAVAILABLE`; it is not downtime. Statping is only a candidate provider and is not bundled or required by this release.
