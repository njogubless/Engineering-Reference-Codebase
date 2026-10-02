# 07 · Networking (API client)

> One typed HTTP client per app. It owns timeouts, cancellation, retries,
> request IDs and error mapping, so no screen or component reimplements them.

## The problem

`fetch(url)` or `dio.get(url)` called directly from UI code works in the demo
and fails in production:
- no timeout, so a spinner hangs forever on a stalled connection;
- no cancellation, so a closed screen still receives (and applies) a late response;
- no error mapping, so every caller parses errors differently, or doesn't;
- either no retries (one dropped packet means an error screen), or naive
  retries that repeat a payment.

## The pattern

```text
UI ─► state (TanStack Query / Riverpod) ─► repository / api module ─► HTTP client ─► network
                                                                      │
                                     timeouts · cancellation · request ID · logging
                                     retry (idempotent only) · error → AppError
```

| Concern | Rule |
|---|---|
| Timeouts | Every request has one (default 10 s; connect 5 s on Flutter). |
| Cancellation | Callers pass a signal/token. A caller cancelling is `cancelled` and is **never retried**. A timeout is `timeout` and **may** be retried. |
| Retries | Only for requests that are **safe to repeat**: `GET/HEAD/PUT/DELETE/OPTIONS`, or any request with an `Idempotency-Key`. Only for transient failures: network errors, timeouts, 429, 502, 503, 504. |
| Backoff | Exponential with *full jitter*: `delay = random(0, min(max, base × 2^(attempt-1)))`. `Retry-After` wins when present (capped). |
| Request ID | One `X-Request-ID` per *logical* request, shared by its retries, so server logs show "same request, attempt 2". |
| Errors | Everything thrown is `AppError` (see [30-error-handling](../30-error-handling/README.md)). |
| Logging | Method, path (no query string), status, duration, attempt, request ID. Never headers or bodies. |
| Retry layers | Retry in **exactly one** layer. TanStack Query (`retry: false`) and Riverpod 3 (`retry: (_, _) => null`) have their own retries, which are disabled because the HTTP client already retries. |

## When to use it

Any app that calls an HTTP API more than once.

## When not to

Don't wrap the client in further generic layers (`BaseApiService`,
`ApiRepository<T>`). Feature code calls the client directly, through
`features/<name>/api.ts` (React) or a repository (Flutter).

## How it is implemented

| | React | Flutter |
|---|---|---|
| Transport | native `fetch` + `AbortController` (no axios) | Dio |
| Timeouts | per-attempt `AbortController` aborted with a `TIMEOUT` reason | Dio `connect/send/receiveTimeout` |
| Cancellation | caller's `AbortSignal` (TanStack Query passes one) | `CancelToken`, cancelled in `ref.onDispose` |
| Retries | loop inside `request()` | `RetryInterceptor` re-dispatching with `dio.fetch` |
| Error mapping | `parseResponse` + `fetchWithTimeout` | `mapDioException` |
| Typed results | `http.get<Meta>()` with types generated from the contract | repository parses JSON into models (`ServerMeta.fromJson` → `ParseError` on bad shape) |
| Code | [src/lib/http.ts](../../../react/reference_app/src/lib/http.ts) | [lib/core/networking/](../../../flutter/reference_app/lib/core/networking/) |
| Tests | [http.test.ts](../../../react/reference_app/src/lib/http.test.ts) (MSW intercepts real `fetch`) | [api_client_test.dart](../../../flutter/reference_app/test/core/networking/api_client_test.dart) (fake `HttpClientAdapter`, real Dio pipeline) |

### What stays the same

The retry policy, the idempotency rule, the request-ID rule, the error type,
and the rule of exactly one retry layer.

### What changes because of the ecosystem

- **React** builds on `fetch`, which has everything needed. Distinguishing a
  timeout from a user cancel uses `AbortController.abort(reason)`.
- **Flutter** builds on Dio's interceptor chain. Order matters: request ID →
  logging → retry, so each retried attempt is logged.
- **Flutter** validates JSON in model factories (`fromJson` with Dart 3
  patterns). React trusts the generated types for shape. A runtime validator
  (zod) arrives with forms in Phase 5.

### Trade-offs

- Retrying in the client hides brief outages from users, but adds latency
  before an error shows (bounded: 2 retries, ≤ 5 s each).
- The per-request `retries` override (`0` for health probes and polling)
  keeps "report current state" calls honest.

## Common mistakes

| ❌ Problematic | ✅ Recommended |
|---|---|
| Retrying `POST /payments` on a 503 | Only idempotent methods, or attach an `Idempotency-Key` the server honours |
| Retries in the HTTP client *and* TanStack Query/Riverpod (3 × 3 = 9 attempts) | Retry in one layer and turn the others off |
| Fixed retry delay | Exponential backoff + jitter, so clients don't retry in lock-step |
| Ignoring `Retry-After` | Honour it (capped) |
| Treating a user cancel like a failure (error toast, retry) | Distinct `cancelled` code, never retried, never shown as an error |
| No timeout | A timeout on every request |
| A new request ID per retry | One ID per logical request |
| Logging request bodies "for debugging" | Never; they contain passwords, tokens and personal data |

## Edge cases covered by tests

Query params with `null`/`undefined` are dropped (never sent as `"undefined"`);
`204 No Content`; non-JSON error bodies; invalid JSON in a success response;
already-aborted signals; cancellation mid-flight versus before sending; `Retry-After`
capping; per-request retry override; a 503 readiness response treated as data
(`acceptStatuses`).

## Adapting it to a real project

- Add the auth header and single-flight token refresh as one more layer
  (Phase 3). The request ID and retry layers don't change.
- Keep the defaults (timeouts, retries) in one place and override per
  request, not per feature.
- For uploads and downloads (Phase 9), Dio's progress callbacks and
  `XMLHttpRequest`/`fetch` streams plug into the same client.
