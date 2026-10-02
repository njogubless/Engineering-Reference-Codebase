# 0001 · Design-first OpenAPI contract implemented by both backends

**Status:** Accepted (2026-10-02)

## Context
The repository demonstrates the same API in Django and FastAPI, consumed by
React and Flutter. Without one source of truth the four drift apart and the
cross-stack comparison stops being a comparison.

## Decision
`contracts/openapi.yaml` is hand-written and reviewed like code. Both backends
implement it. CI verifies operation parity (generated schema vs contract),
response conformance (Schemathesis) and error shapes. React types are
generated from it; Flutter DTOs are hand-written.

## Consequences
- Either client can talk to either backend.
- Adding an endpoint means editing the contract first, then both backends.
- Framework-generated schemas (drf-spectacular, FastAPI) remain useful as
  drift detectors, not as documentation.

## Rejected
- **Code-first from one backend:** the other backend would copy accidents.
- **Generated clients:** harder to read and customise than a small hand-written client.
