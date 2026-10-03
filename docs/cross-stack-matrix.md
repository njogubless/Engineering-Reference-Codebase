# Cross-Stack Matrix

**This file is the single source of truth for implementation status.**
Definitions live in [pattern-catalogue.md](pattern-catalogue.md). The gates a cell
must pass are in [implementation-roadmap.md § Definition of Done](implementation-roadmap.md#definition-of-done).

| Symbol | Meaning |
|---|---|
| ⬜ | Not started |
| 🟨 | In progress, or partially verified |
| 🧪 | Done, but verified only against emulators/fakes (real credentials or a device are required for full verification; see architecture §8) |
| ✅ | Done: every Definition-of-Done gate verified |
| ➖ | Not applicable to this stack |

`Platform` = Firebase rules/emulator, Docker, CI, Postgres/Redis configuration, or `contracts/`.
`Docs` = concept README in `docs/patterns/` or `docs/common-problems/`.

_Last verified: 2026-10-03 (end of Phase 2) — `make check` green: Django 117 tests, FastAPI 88, React 74, Flutter 65, contract 48 (authenticated, deterministic Schemathesis on both backends); React verified against the seeded Django API in a browser._

## Foundations & cross-cutting

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Project scaffold + quality gate (format/lint/type/test/build) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| CI workflow per stack | ➖ | ➖ | ➖ | ➖ | 🟨 ¹ | ✅ | 1 |
| Docker Compose dev environment | ➖ | ➖ | ➖ | ➖ | ✅ | ✅ | 1 |
| Dependency management (lockfiles, update bot, audit) | ✅ | ✅ | ✅ | ✅ | 🟨 ¹ | ✅ | 1 |
| Configuration (typed, env-driven, fail-fast, `.env.example`) | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 1 |
| Feature flags | 🟨 ² | 🟨 ² | ✅ | ✅ | ➖ | ✅ | 1 |
| Error model (Problem Details ↔ AppError) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| Global error capture (boundary / onError) | 🟨 ³ | 🟨 ³ | ✅ | ✅ | ➖ | ✅ | 1 |
| Swallowed exceptions (bad vs good) | ➖ | ➖ | ✅ | ➖ | ➖ | ✅ | 1 |
| Structured logging + redaction | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 1 |
| Request ID propagation | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 1 |
| Health / liveness / readiness | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | 1 |
| OpenAPI contract skeleton + drift/conformance tests | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | 1 |
| CORS (incl. on error responses, exposed headers) | ➖ | ➖ | ✅ | ✅ | ➖ | ✅ | 1 |
| API client (verbs, timeouts, cancel, error mapping) | ✅ | ✅ | ➖ | ➖ | ➖ | ✅ | 1 |
| Client retry with backoff + jitter (idempotent only, one layer) | ✅ | ✅ | ➖ | ➖ | ➖ | ✅ | 1 |
| Strict input (unknown fields, no type coercion, NUL/surrogates, all errors at once) | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | 2a |
| Outbound retry/backoff for provider calls | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 11 |

¹ Workflows and Dependabot config are written and YAML-validated, and every step they run passes locally via the same Makefile targets, but they have not yet run on GitHub (no remote configured).
² Clients read and display public flags from `GET /api/v1/meta`; no client UI is flag-gated yet (first real use: Phase 6 `search_v2`).
³ React's render-error boundary is tested; the root `onUncaughtError`/`unhandledrejection` hooks (React) and `FlutterError.onError`/`PlatformDispatcher.onError` (Flutter) are wired but not under test. Forwarding to an error tracker is Phase 15.

## Data, state & contracts

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Domain models, constraints, indexes, migrations | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | 2a |
| CRUD resource (Posts/Comments) | 🟨 ¹⁰ | ✅ | ✅ | ✅ | ✅ | ✅ | 2a/2b |
| Contract conformance tests (authenticated Schemathesis, error parity) | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | 2a |
| Generated client types from OpenAPI | ➖ ¹¹ | ✅ | ➖ | ➖ | ✅ | ✅ | 2 |
| DTO ↔ entity mapping | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 2 |
| Repository / data source layering | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 2 |
| Firestore CRUD, streams, queries, ordering | 🧪 | ➖ | ➖ | ➖ | ⬜ | ✅ | 2b/3 |
| Firestore transactions, batched writes, subcollections | 🧪 | ➖ | ➖ | ➖ | ⬜ | ✅ | 2b/3 |
| Riverpod provider types (each with a reason) | 🟨 ¹² | ➖ | ➖ | ➖ | ➖ | ✅ | 2b |
| Async UI states (loading/success/error/empty/refreshing) | ✅ | ✅ | ➖ | ➖ | ➖ | ✅ | 2b |
| Server-state cache + invalidation | ✅ | ✅ | ➖ | ➖ | ➖ | ✅ | 2b |
| State categories (local/server/form/URL/global) | ➖ | 🟨 ¹³ | ➖ | ➖ | ➖ | ✅ | 2b |
| Optimistic update + rollback | ✅ | ✅ | ➖ | ➖ | ➖ | ✅ | 2b |
| Date/time handling (UTC wire, local display) | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 2 |

⁶ Register, login, logout and `/me` are done; password reset and email verification need transactional email (Phase 3 with Mailpit).
⁷ Author-only writes; visible-but-not-yours → 403, invisible → 404. Roles and RBAC are Phase 4.
⁸ Query counts are asserted (1 per post page; FastAPI relationships use `lazy="raise"`), but the bad-vs-good demo is Phase 7.
⁹ Argon2id with constant-time-equivalent login (dummy hash for unknown emails); brute-force throttling is Phase 14.

¹⁰ Flutter lists, reads and publishes/unpublishes against the API; creating, editing and deleting from the UI comes with forms in Phase 5 (the repository already implements them, and they are tested).
¹¹ Flutter DTOs are hand-written by decision ([36-api-contracts](patterns/36-api-contracts/README.md)).
¹² `StreamProvider` is used with Firestore in Phase 3; every other type listed in the guide is in use and tested.
¹³ Local, server, session and form state are in place; URL state arrives with routing (Phase 4) and filters (Phase 6).
¹⁴ "Load more" button + cursor; infinite scroll on scroll position and virtualization are Phase 6.

## Authentication

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Firebase email (register/login/logout/verify/reset/change/delete) | ⬜ | ⬜ | ➖ | ➖ | ⬜ | ⬜ | 3 |
| Firebase Google sign-in + account linking | ⬜ | ⬜ | ➖ | ➖ | ⬜ | ⬜ | 3 |
| Firebase phone OTP (send/verify/resend/timeout/invalid) | ⬜ | ⬜ | ➖ | ➖ | ⬜ | ⬜ | 3 |
| Auth state machine + session restoration | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 3 |
| Firebase ID-token verification → local user | ➖ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 3 |
| First-party register/login/logout/reset/verify email | ➖ | ⬜ | 🟨 ⁶ | 🟨 ⁶ | ➖ | 🟨 | 2a/3 |
| Session auth + CSRF | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 3 |
| Access + rotating refresh tokens, revocation (FastAPI: reuse detection) | ➖ | ⬜ | ✅ | ✅ | ➖ | ✅ | 2a |
| Single-flight refresh interceptor | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 3 |
| Secure token storage (bad vs good) | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 3 |

## Authorization & routing

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| RBAC (user/manager/admin/superadmin) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 4 |
| Object-level / ownership permissions | ➖ | ➖ | 🟨 ⁷ | 🟨 ⁷ | ➖ | ⬜ | 2a/4 |
| Staff/admin access, admin hardening | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 4 |
| Client permission state | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 4 |
| Firestore/Storage security rules + rules tests | ➖ | ➖ | ➖ | ➖ | ⬜ | ⬜ | 4 |
| Authorization bugs (bad vs good) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 4 |
| Public/protected routes, guards, redirects | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 4 |
| Nested routes, layouts, path + query params | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 4 |
| 404 / unknown routes, modal routes | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 4 |
| Bottom/nested navigation with preserved state | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 4 |
| Deep links (incl. resume-after-login) | ⬜ | ⬜ | ➖ | ➖ | ⬜ | ⬜ | 4 |
| Lazy route modules / code splitting | ➖ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 4 |

## Forms, lists & search

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Forms: login/registration/profile/password | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 5 |
| Multi-step + dynamic forms, restoration | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 5 |
| Async + server validation → field errors | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 5 |
| Double-submit prevention | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 5 |
| Offset pagination | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 6 |
| Cursor / keyset pagination | ✅ | ✅ | ✅ | ✅ | ➖ | ✅ | 2a/2b |
| Firestore cursor pagination | 🧪 | ➖ | ➖ | ➖ | ➖ | ✅ | 2b |
| Infinite scroll, pull-to-refresh, end-of-list, dedupe | ✅ | 🟨 ¹⁴ | ➖ | ➖ | ➖ | ✅ | 2b/6 |
| Unbounded query (bad vs good) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 6 |
| Debounced, race-free search + history | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 6 |
| Filtering + sorting (whitelisted) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 6 |
| Postgres full-text + trigram search | ➖ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 6 |
| URL-synced list state | ➖ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 6 |
| Virtualized large lists | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 6 |

## Database depth, concurrency & idempotency

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| N+1 queries (bad vs good, query-count tests) | ➖ | ➖ | 🟨 ⁸ | 🟨 ⁸ | ➖ | ⬜ | 7 |
| Index-defeating lookups (EXPLAIN-tested) | ➖ | ➖ | ✅ | ➖ | ➖ | ✅ | 2a |
| Annotations + aggregations | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Soft deletion | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Audit log | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 7 |
| Zero-downtime migrations + backfill | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Transaction boundaries (`on_commit`) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Pessimistic locking: inventory + wallet races | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Optimistic locking (version / ETag → 409) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Idempotency-Key handling | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Duplicate requests (bad vs good) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 7 |
| Distributed lock (Redis) and its limits | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 7 |

## Caching

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Redis cache-aside, TTL, key versioning | ➖ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 8 |
| Per-view caching (and per-user pitfall) | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 8 |
| Invalidation on write + stampede protection | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 8 |
| HTTP caching (ETag / Cache-Control) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 8 |
| Client cache policy (stale time, keepAlive) | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 8 |
| Stale cache (bad vs good) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 8 |

## Files

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Server upload validation (size, magic bytes) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 9 |
| Storage abstraction (local / S3 / Firebase Storage) | ⬜ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 9 |
| Presigned upload + signed download URLs | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | 9 |
| Deletion + orphan cleanup | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 9 |
| Picker/camera/gallery, multiple files, preview | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 9 |
| Upload progress + cancellation, download | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 9 |
| Image processing job (thumbnails) | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 9 |

## Background processing, email & events

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Celery worker + beat schedules | ➖ | ➖ | ⬜ | ➖ | ⬜ | ⬜ | 10 |
| Task retries, backoff, time limits | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 10 |
| Idempotent tasks + enqueue on commit | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 10 |
| Dead-letter / failure store + replay | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 10 |
| In-process background tasks (and limits) | ➖ | ➖ | ➖ | ⬜ | ➖ | ⬜ | 10 |
| Transactional outbox | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 10 |
| Transactional email (templates, Mailpit) | ➖ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 10 |

## Webhooks & payments

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Webhook signature verification | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Persist-then-ack + async processing | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Webhook idempotency + out-of-order events | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Payment state machine | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Provider adapter: Fake | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Provider adapter: Stripe | ➖ | ➖ | ⬜ | ➖ | ⬜ | ⬜ | 11 |
| Provider adapter: M-Pesa (Daraja STK Push) | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 11 |
| Provider adapter: Airtel Money | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 11 |
| Double-payment prevention | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Reconciliation job | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 11 |
| Money handling (minor units, currency) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 11 |
| Client payment flow (initiate, pending, status) | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 11 |

## Notifications & real-time

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| FCM permission, token register/refresh/invalidate | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 12 |
| Foreground/background messages, tap → deep link | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 12 |
| Backend device registry + send + prune | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 12 |
| In-app notifications (read/unread) | ⬜ | ⬜ | ⬜ | ➖ | ➖ | ⬜ | 12 |
| WebSockets (auth, heartbeat, reconnect) | ⬜ | ⬜ | ➖ | ⬜ | ➖ | ⬜ | 12 |
| Server-Sent Events | ➖ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 12 |
| Redis pub/sub fan-out | ➖ | ➖ | ➖ | ⬜ | ⬜ | ⬜ | 12 |

## Offline & local storage

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Preferences / secure storage / Drift (each justified) | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 13 |
| Connectivity state + offline UI | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 13 |
| Cache-then-network reads | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 13 |
| Queued writes + sync + retry | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 13 |
| Conflict handling (version-based) | ⬜ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 13 |

## Security

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Rate limiting | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 14 |
| CSRF, secure headers, CSP (CORS done in Phase 1) | ➖ | ⬜ | 🟨 ⁴ | ⬜ | ⬜ | 🟨 | 14 |
| SQL injection (bad vs good) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 14 |
| XSS (bad vs good) | ➖ | ⬜ | ⬜ | ➖ | ➖ | ⬜ | 14 |
| Password hashing + brute-force protection | ➖ | ➖ | 🟨 ⁹ | 🟨 ⁹ | ➖ | 🟨 | 2a/14 |
| Secrets management + secret scanning | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | 14 |
| Dependency + container scanning | ➖ | ➖ | ➖ | ➖ | ⬜ | ⬜ | 14 |
| PII minimization, account deletion, data export | ⬜ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 14 |

⁴ Deployed-environment transport settings (SSL redirect, secure cookies, X-Frame-Options, CSRF middleware) are in place; `check --deploy` leaves only the deliberate HSTS opt-in warning.

## Observability

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Error tracking (Sentry / Crashlytics) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 15 |
| Metrics (Prometheus) | ➖ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 15 |
| Tracing (OpenTelemetry) | ➖ | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | 15 |
| Analytics events | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 15 |
| Circuit breaker for providers | ➖ | ➖ | ⬜ | ➖ | ➖ | ⬜ | 15 |

## Performance, accessibility, i18n

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Unnecessary rebuilds/renders (bad vs good) | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 16 |
| Memory leaks / disposal (bad vs good) | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 16 |
| Isolates / heavy work off the main thread | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 16 |
| Image caching, resizing, optimization | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 16 |
| Bundle analysis + splitting | ➖ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 16 |
| Large payloads, streaming responses, compression | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 16 |
| Internationalization + localized formatting | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 16 |
| Accessibility + automated a11y checks | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 16 |

## Testing depth, delivery & documentation

| Pattern | Flutter | React | Django | FastAPI | Platform | Docs | Phase |
|---|---|---|---|---|---|---|---|
| Integration tests (device/browser) | ⬜ | ⬜ | ⬜ | ⬜ | ➖ | ⬜ | 17 |
| Golden tests | ⬜ | ➖ | ➖ | ➖ | ➖ | ⬜ | 17 |
| E2E (Playwright) | ➖ | ⬜ | ➖ | ➖ | ⬜ | ⬜ | 17 |
| Production images (multi-stage, non-root), Nginx | ➖ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | 18 |
| Deployment workflow + migrations on deploy | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | 18 |
| App versioning, forced update, release channels | ⬜ | ⬜ | ➖ | ➖ | ➖ | ⬜ | 18 |
| Design patterns (linked to real code) | ➖ | ➖ | ➖ | ➖ | ➖ | ⬜ | 19 |
| Engineering principles with examples | ➖ | ➖ | ➖ | ➖ | ➖ | ⬜ | 19 |
| Architecture styles, good vs over-engineered | ➖ | ➖ | ➖ | ➖ | ➖ | ⬜ | 19 |
| Software lifecycle | ➖ | ➖ | ➖ | ➖ | ➖ | ⬜ | 19 |
| Scalability concepts | ➖ | ➖ | ➖ | ➖ | ➖ | ⬜ | 19 |
| Multi-tenancy (optional) | ➖ | ➖ | ⬜ | ⬜ | ➖ | ⬜ | 19 |
