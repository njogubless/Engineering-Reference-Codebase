# 31 · Logging and request IDs

> Structured JSON logs with a request ID on every line, and a hard rule about
> what never gets logged.

## The problem

`print(f"user {user} failed to pay: {error}")` gives you logs you can't
search, can't connect to the request that produced them, and that eventually
contain a password or a card number.

## The pattern

1. **Events, not sentences.** The message is a stable event name
   (`order_placed`, `readiness_check_failed`). Context goes in fields:
   `logger.info("order_placed", extra={"order_id": 7})`.
2. **JSON in deployed environments**, readable console output locally (`LOG_FORMAT`).
3. **Every line carries `request_id`.** The ID is accepted from the client
   (`X-Request-ID`, validated) or generated, stored in a `ContextVar`, attached
   to every log record, echoed in the response header, and included in every
   Problem body. One ID connects a user's error screen, the client log and the server log.
4. **One completion line per request** (FastAPI: `request_completed` with
   method, path, status, duration).
5. **Redaction is a safety net, not the plan.** Keys that look sensitive are
   replaced with `[REDACTED]`, but the rule is not to pass secrets to the logger at all.

## What to log, and what never to log

| ✅ Log | ❌ Never log |
|---|---|
| event name, IDs (request, user, order) | passwords, OTPs, password-reset tokens |
| HTTP method, path **without query string**, status, duration | `Authorization` headers, cookies, access/refresh tokens, API keys |
| error codes, exception type + traceback (server side) | request/response bodies |
| retry attempts, dependency failures | card numbers, CVV, full bank details |
| | personal data beyond an opaque user ID (emails, phone numbers, addresses) |

Query strings are excluded because they often carry tokens (`?token=...`
in reset links, signed URLs).

## How it is implemented

| | Django | FastAPI | React | Flutter |
|---|---|---|---|---|
| Format | stdlib `logging` + `JsonFormatter` | same module (each backend is standalone) | `logger` with levels | `AppLogger` with levels |
| Request context | `RequestIdMiddleware` + `ContextVar` | pure-ASGI `RequestContextMiddleware` + `ContextVar` | generates one ID per logical request | `RequestIdInterceptor` |
| Redaction | `redact()` on `extra` | same | `redact()` | `redact()` |
| Code | [apps/core/logging.py](../../../django/reference_api/apps/core/logging.py), [middleware.py](../../../django/reference_api/apps/core/middleware.py) | [app/core/logging.py](../../../fastapi/reference_api/app/core/logging.py), [middleware.py](../../../fastapi/reference_api/app/core/middleware.py) | [src/lib/logger.ts](../../../react/reference_app/src/lib/logger.ts) | [lib/core/logging/app_logger.dart](../../../flutter/reference_app/lib/core/logging/app_logger.dart) |

### Why a `ContextVar`, not a thread-local

It is correct under both WSGI threads and ASGI tasks. Middleware always
resets it in `finally`, otherwise a later request on the same worker would
inherit the ID (tested: "context is cleared after the request").

### Why incoming IDs are validated

A client-supplied ID ends up in every log line. Without the
`^[A-Za-z0-9._-]{1,128}$` check, a client could inject newlines (fake log
lines) or megabyte-sized values.

### Ecosystem notes

- Django's `django.request` logger is limited to `ERROR`. Expected 4xx
  responses aren't operational problems.
- Uvicorn writes its access log outside the request context (no request ID),
  so it is silenced and the middleware's `request_completed` line replaces it.
- No structlog or python-json-logger dependency: a 40-line formatter does the job.
- Clients keep only warnings and errors in release builds. Forwarding them to
  Sentry/Crashlytics comes in Phase 15.

## Common mistakes

| ❌ | ✅ |
|---|---|
| `logger.info(f"payment {payment} failed")` | `logger.info("payment_failed", extra={"payment_id": payment.id})` |
| `logger.debug("request", extra={"headers": request.headers})` | log the specific, safe fields you need |
| logging full URLs | log the path; drop the query string |
| a new request ID per retry | one ID per logical request |
| the same log line in five layers | log once, where the error is handled |
