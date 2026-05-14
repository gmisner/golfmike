# Sample XML

This folder holds example payloads for development and regression checks.

## Ingestable (`Ingestable/`)

Curated **TFM / SWIM** XML that the traffic pipeline is expected to route, parse, and store. Used by:

- `./tools/audit_ingestable_samples.sh` (strict + fail-on-unroutable)
- CI job **audit-ingestable**

Add new files here only when they should pass that gate.

## Weather (`Weather/`)

**ITWS / weather product** examples. They are **not** TFM `fltdMessage` payloads, so they do not appear in the ingestable audit and are not expected to have a `msgType` registry mapping.

## Full `Sample XML/` directory

May include large multiplexed dumps (for example `FlightScheduleActivate.xml`, `trackinformation.xml`). The ingestable subset copies a stable slice of those plus small single-message fixtures for faster, stricter CI.
