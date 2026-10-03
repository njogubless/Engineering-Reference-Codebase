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
- Pagination: explicit `PostPage`/`CommentPage` schemas with `next_cursor` (no allOf "generics": they generate `unknown[]`) (see [11-pagination](../11-pagination/README.md)).
- Security: bearer JWT by default (top-level `security`); public operations opt out with `security: []`.
- Input strictness: unknown body fields → 422 `unknown_field`; wrong JSON types are
  rejected, never coerced; NUL and unpaired surrogates → 422; unknown query
  parameters are ignored.

## What the contract tests found

Phase 2 added authenticated Schemathesis runs against both backends. The
first runs failed 12 operations, and later randomized runs kept finding more. Every failure was real, and each led to a
change in code, contract or test configuration:

| Finding | Backend | Fix |
|---|---|---|
| A NUL byte in a login email reached PostgreSQL → **500** | FastAPI | `SafeChars` validator (NUL / unpaired surrogates → 422, DRF's codes) |
| `"\f"` as a title was stripped to `""` *after* the length check; the DB `CHECK` refused it → **500** | FastAPI | Pydantic metadata order: constraints first, custom validator last (regression test) |
| `{"refresh": 0}` accepted: DRF coerced the number to `"0"` | Django | `StrictInputMixin`: string fields accept only JSON strings |
| Unknown fields reported alone, hiding the other field errors | Django | report all errors at once, as Pydantic does |
| 405 without a complete `Allow` header (FastAPI nests routers; Starlette saw one route) | FastAPI | compute `Allow` through `BaseRoute.matches()` |
| Password "too similar" check stricter in FastAPI (substring) than Django (similarity ratio) | FastAPI | ported Django's algorithm: both accept the same passwords |
| Empty strings and whitespace-only titles were schema-valid | contract | `minLength: 1` + a `non_blank` pattern |
| `"\x1f"` matched JSON Schema's `\S` but Python's `str.strip()` removes it, so "valid" titles were rejected | contract | `non_blank` lists Python's exact whitespace set; a test checks all 1.1M code points |
| Pydantic's `strip_whitespace` (Rust, Unicode `White_Space`) keeps `"\x1d"`; DRF strips it, so a title was accepted by one backend only | FastAPI | `PythonStrip` validator: trim the way DRF does |
| A whitespace-only refresh token: 422 from Django (DRF trims), 401/204 from FastAPI | both + contract | `non_blank` on token fields; FastAPI `NonBlank` (rejects without altering the token) |
| **simplejwt trims the login password** while registration doesn't: a password ending in a space could be set but never used | Django | `ObtainTokenSerializer` with an untrimmed `PasswordField` (regression test) |
| DRF skips invalid base64 characters in cursors, so a 600-character garbage cursor served page 1 | Django | strict base64 + length check before DRF decodes |

**Deterministic gate, exploratory fuzzing.** Random inputs kept finding new
issues across runs, which is valuable, but in CI it means a red build for an
unrelated change. `make check-contract` is therefore deterministic (same
commit, same result), and `make fuzz-contract` runs 500 fresh random examples
per operation. Every fuzzing finding becomes a regression test in the
backend's own suite.

Configuration (`tests/contract/schemathesis.toml`) records the deliberate
exceptions: 422 is an expected answer for business rules a schema can't
express (password strength, opaque cursors); unknown query parameters are
ignored by design; NUL bytes are excluded from generation because the
contract forbids them and each backend tests that directly.

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
