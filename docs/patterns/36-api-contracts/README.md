# 36 · API Contracts

> A hand-written OpenAPI document is the source of truth. Both backends are
> tested against it, and the TypeScript client's types are generated from it.

## The problem

With code-first API docs, the documentation describes whatever the code
happens to do, including its accidents. With two backends and two clients,
"whatever the code does" quickly becomes four slightly different APIs.

## The pattern: design-first, verified

```text
                    contracts/openapi.yaml  (reviewed like code)
                    │          │            │
          lint (Spectral)      │            └──► openapi-typescript ──► React types
                               │
          tests/contract ──────┼──► Django   (drf-spectacular schema + live responses)
                               └──► FastAPI  (FastAPI schema + live responses)
```

`make check-contract` ([scripts/contract-check.sh](../../../scripts/contract-check.sh)) does four things:

1. **Lint:** Spectral (`spectral:oas` + every operation needs an `operationId`
   and tags), failing on warnings.
2. **Operation drift:** each backend's *generated* OpenAPI must expose exactly
   the contract's `(path, method, operationId)` set. This catches endpoints
   added to only one side.
3. **Conformance:** Schemathesis generates requests from the contract and
   validates every response's status, content type and body against it, for
   both running backends.
4. **Error shapes:** forced 404 and 405 responses from both backends are
   validated against the contract's `Problem` schema, including request-ID echo.

Verified to bite: changing `Meta.api_version` to `const: "2"` in the contract
makes both backends' conformance tests fail.

## Client types

React: `pnpm gen:api` writes `src/lib/api/schema.d.ts`. The gate regenerates
it and fails if the committed file differs (`git diff --exit-code`). Feature
code uses `components['schemas']['Meta']`. **Types are generated; the client
is hand-written** (see [07-networking](../07-networking/README.md)), because
generated clients tend to be harder to read and customise than the 200 lines
they replace.

Flutter: DTOs are hand-written with validating `fromJson` factories (Dart 3
patterns). Generating Dart from OpenAPI (`openapi-generator`'s `dart-dio`)
works, but produces a lot of code and a build step. It's worth it once the
API has dozens of models. That alternative is documented, not adopted.

## Conventions in the contract

- Errors: `Problem` (RFC 9457) with the `ErrorCode` enum ([30-error-handling](../30-error-handling/README.md)).
- Versioning: `/api/v1/...` (health probes are unversioned).
- `X-Request-ID` header on every response.
- Pagination shapes (`CursorPage`, `OffsetPage`) arrive with the first list endpoint in Phase 2.

## When not to use design-first

For a single backend with a single first-party client, code-first
(drf-spectacular/FastAPI generating the document) plus a check that the
generated document is committed and reviewed is a reasonable, cheaper option.
This repository has two backends that must agree, which is exactly where
design-first earns its cost.

## Common mistakes

| ❌ | ✅ |
|---|---|
| Docs generated from code and never reviewed | Contract changes reviewed like code; drift fails CI |
| Hand-copied TypeScript interfaces | Generated types, regenerated in CI |
| Breaking changes in place (`/api/v1` changes meaning) | Additive changes only within a version; new version for breaking ones |
| Error responses missing from the contract | One `Problem` response referenced everywhere |
