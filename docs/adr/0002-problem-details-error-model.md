# 0002 · RFC 9457 Problem Details + one client error type

**Status:** Accepted (2026-10-02)

## Decision
Every API error is `application/problem+json` with a stable `code` from a
fixed enum, `request_id`, and `errors[]` for field errors. Validation is 422
and malformed input is 400 in both backends (overriding DRF's 400 and
FastAPI's blanket 422). Clients map every failure, including network,
timeout, cancellation and parse failures, into one `AppError` type and
present it through one exhaustive `userMessage` function.

## Consequences
- UI code never parses error bodies.
- New codes are a contract change and fail client type checks until handled.
- FastAPI's unexpected-error handling lives in middleware, because Starlette
  runs `Exception` handlers outside user middleware (no request ID, no CORS).

## Rejected
- Framework defaults (`{"detail": ...}`): different per framework and unstructured.
- A custom envelope (`{"error": {...}}`): a standard already exists.
