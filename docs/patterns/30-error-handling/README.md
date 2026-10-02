# 30 · Error Handling

> One error model across every stack: the backend speaks RFC 9457 Problem
> Details, and each client turns every failure into a single `AppError` type.

## The problem

Without a deliberate design, errors leave an API in whatever shape the
framework or the crashing line of code produced. That might be DRF's
`{"detail": ...}`, FastAPI's `{"detail": [...]}`, Django's HTML 404 page, a
proxy's HTML 502 page, or a stack trace. Clients then end up with code like
`if (e.response?.data?.detail?.[0]?.msg)` scattered through components. Users
see raw technical strings, and support can't connect a user's complaint to a log line.

## The pattern

```text
Backend                      Wire                         Client
───────                      ────                         ──────
serializer / pydantic  ┐                                 ┌─► AppError ─► state ─► UI message
service (domain error) ├─► exception handler ─► Problem ─┤   (one type; exhaustive switch on code)
unexpected crash       ┘   (one place)          JSON     └─ + client-only failures:
                                                            network, timeout, cancelled, parse
```

1. **One wire format.** Every error is `application/problem+json` with a
   stable machine-readable `code`, the `request_id`, and `errors[]` for field
   errors. See `Problem` in [contracts/openapi.yaml](../../../contracts/openapi.yaml).
2. **One translation point per backend.** Handlers convert framework and
   domain exceptions into Problems. Business code never builds HTTP responses.
3. **One error type per client.** The HTTP client is the only code that sees
   transport exceptions. Everything above it sees `AppError`.
4. **One presentation function per client.** `userMessage(error)` switches on
   the code, and the switch is exhaustive, so adding a code fails the build
   until the UI handles it.

| Code | HTTP | Raised when |
|---|---|---|
| `bad_request` | 400 | malformed request (e.g. invalid JSON) |
| `validation_error` | 422 | well-formed but invalid input; details in `errors[]` |
| `authentication_error` | 401 | missing, invalid or expired credentials |
| `authorization_error` | 403 | authenticated but not allowed |
| `not_found` | 404 | resource missing, or hidden for authorization reasons |
| `method_not_allowed` | 405 | wrong HTTP method |
| `unsupported_media_type` | 415 | body is not JSON |
| `conflict` | 409 | stale version, duplicate, idempotency key in flight |
| `idempotency_key_reused` | 422 | same key, different payload |
| `rate_limited` | 429 | throttled; `Retry-After` header + `retry_after` field |
| `external_service_error` | 502 | a provider we depend on failed |
| `internal_error` | 500 | anything unexpected; never includes internal details |
| *client only:* `network_error`, `timeout`, `cancelled`, `parse_error` | – | no usable response |

## When to use it

Always, from the first endpoint. Changing the error format later is a
breaking change for every client.

## When not to

There is no API where ad-hoc errors are better. A server-rendered app with
no API clients can rely on the framework's error pages for HTML routes, but
its JSON endpoints still need this.

## How it is implemented

| | Django | FastAPI | React | Flutter |
|---|---|---|---|---|
| Translation point | one DRF `EXCEPTION_HANDLER` + `handler404/500` for non-DRF paths | one handler per exception type + middleware for crashes | `parseResponse` in the HTTP client | `mapDioException` |
| Domain errors | Django's own `ValidationError`, `PermissionDenied`, `Http404`, plus `ConflictError`, `ExternalServiceError` | `AppError` subclasses (`NotFoundError`, `ConflictError`, ...) | – | – |
| Client error type | – | – | `class AppError extends Error` with `code` union | `sealed class AppError` with subtypes |
| User message | – | – | `userMessage()` with `assertNever` | `userMessage()` with exhaustive `switch` |
| Code | [apps/core/errors.py](../../../django/reference_api/apps/core/errors.py) | [app/core/errors.py](../../../fastapi/reference_api/app/core/errors.py), [middleware.py](../../../fastapi/reference_api/app/core/middleware.py) | [src/lib/errors.ts](../../../react/reference_app/src/lib/errors.ts) | [lib/core/errors/](../../../flutter/reference_app/lib/core/errors/) |

### What stays the same conceptually

- The codes, statuses and body shape (verified for both backends by `tests/contract/test_problem_details.py`).
- Field paths: `items.1.name` in both backends. FastAPI's Pydantic error types are mapped to Django's validator codes (`missing` → `required`, `string_too_long` → `max_length`).
- Unexpected errors are logged with the request ID and returned with no details.

### What changes because of the ecosystem

- **Django/DRF** funnels everything through one function. Services raise
  *Django's* exceptions, not DRF's, so business logic doesn't depend on the
  HTTP framework.
- **FastAPI** registers a handler per exception type. One trap: a handler for
  `Exception` runs in Starlette's `ServerErrorMiddleware`, *outside* all user
  middleware, so the request ID is gone and CORS headers are missing. Unexpected
  errors are therefore handled in `RequestContextMiddleware` instead.
- **FastAPI** doesn't check `Content-Type`. A form body sent to a JSON endpoint
  becomes a confusing 422, so the validation handler reports 415 to match DRF.
- **React (TypeScript)** uses one class with a string-union `code`, so it
  works with `instanceof`, has a stack trace, and is exhaustively switchable.
- **Flutter (Dart 3)** uses a `sealed` hierarchy (`ServerError`, `NetworkError`,
  `TimeoutError`, ...) so pattern matching can destructure fields per kind.

### Trade-offs

- Mapping two frameworks onto one table means overriding defaults (DRF uses
  400 for validation, FastAPI 422 for everything). That's a little code, in
  exchange for clients that never care which backend they talk to.
- Hiding internal details makes debugging from the client harder. The
  `request_id` in every body is the bridge to the logs.

## Common mistakes

| ❌ Problematic | ✅ Recommended |
|---|---|
| `except Exception: return None` ([full example](../../common-problems/swallowed-exceptions.md)) | catch only named failures, translate, chain with `from exc` |
| Returning `str(exc)` to the client | log it, and return a generic message + request ID |
| Clients matching on `detail` or `title` text | switch on `code` |
| Validation errors as a single string | `errors[]` with a field path per error |
| Error bodies without CORS headers | CORS middleware outermost; otherwise the browser hides the error from JavaScript |
| UI showing `error.message` | `userMessage(error)`: written for users, translatable |
| Retrying every error | retry only transient ones (see [07-networking](../07-networking/README.md)) |

## Edge cases covered by tests

- Nested and list field errors are flattened to dotted paths; non-field errors have `field: null`.
- Malformed JSON → 400, invalid data → 422, wrong content type → 415.
- `Retry-After` is rounded **up** (retrying 0.4 s early would just be throttled again).
- Unknown URLs return a Problem, not HTML (Django `handler404`, Starlette router).
- A proxy's HTML error page is classified by status on the client.
- A success response with invalid JSON is a `parse_error`, not a crash.
- A 500 response never contains the exception text, but its log record carries the same request ID.

## Adapting it to a real project

1. Copy the code table and add codes sparingly. Each code is a contract the UI must handle.
2. Keep the `type` URIs stable. Pointing them at real documentation pages is a nice touch.
3. Add new domain errors as `AppError` subclasses **per code**, not per situation.
4. Add an error-tracking hook (Sentry/Crashlytics, Phase 15) at the same single points.
