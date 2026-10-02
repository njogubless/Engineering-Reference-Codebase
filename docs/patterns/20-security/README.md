# 20 · Security

> Phase 1 establishes secure defaults and CORS. The full security section
> (rate limiting, CSRF with sessions, CSP, SQLi/XSS bad-vs-good, secret
> scanning) is Phase 14.

## Secure defaults already in place

| Default | Where |
|---|---|
| Deny by default: DRF `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`; public endpoints opt out explicitly (`PublicAPIView`) | Django settings; tested (`test_views_are_deny_by_default`) |
| `DEBUG` off unless explicitly enabled; rejected in staging/production | both backends; tested |
| Strong `SECRET_KEY` required in deployed environments | Django; tested |
| HTTPS redirect, secure cookies, `X-Frame-Options`, CSRF middleware in deployed environments; HSTS opt-in (`SECURE_HSTS_SECONDS`) because browsers cache it | Django settings; `manage.py check --deploy` leaves only the deliberate HSTS warning |
| Errors never contain internals; public health checks never contain error details | both backends; tested |
| Untrusted `X-Request-ID` values are validated before reaching logs | both backends; tested |
| Secrets never in client configuration | [26-configuration](../26-configuration/README.md) |
| Hashed lockfiles (`--require-hashes`) and dependency audits in CI | [01-foundations](../01-foundations/README.md) |

## CORS

Browsers block JavaScript from reading cross-origin responses unless the
server allows that origin. The React dev server (`:5410`) and Flutter web
(`:5420`) are different origins from the APIs (`:8410`, `:8420`).

| Setting | Value | Why |
|---|---|---|
| Allowed origins | explicit list from `CORS_ALLOWED_ORIGINS` | never `*` in deployed environments (FastAPI rejects it at startup) |
| Allowed headers | `authorization`, `content-type`, `x-request-id`, `idempotency-key` | only what clients send |
| Exposed headers | `x-request-id`, `retry-after` | without this, JavaScript cannot read them |
| Preflight cache | 600 s | fewer `OPTIONS` round trips |

**Order matters.** The CORS middleware must wrap everything that can produce
a response, including error handlers. If a 500 response lacks CORS headers,
the browser reports an opaque network error and the client never sees the
Problem body or request ID. Tested in both backends ("error responses carry
CORS headers").

| | Django | FastAPI |
|---|---|---|
| Implementation | `django-cors-headers`, placed before `CommonMiddleware` | Starlette `CORSMiddleware`, added **last** (outermost) |
| Tests | [test_cors.py](../../../django/reference_api/apps/core/tests/test_cors.py) | [test_cors.py](../../../fastapi/reference_api/tests/test_cors.py) |

CORS is not authentication. It stops other *websites* from reading responses
in a user's browser. It does nothing against `curl`.
