# Repository Architecture

> Status: **Accepted** (2026-10-02). Phase 1 implemented this layout; key
> decisions are recorded in [docs/adr/](adr/README.md). Change this document
> before changing the structure, not after.

## 1. What this repository is

A **pattern library with runnable reference implementations**. It is organised
around recurring engineering problems ("pagination", "idempotency",
"token refresh"), and each problem is solved idiomatically in each stack where
it applies.

It has two axes, and the structure exists to keep both navigable:

| Axis | Question it answers | Where it lives |
|---|---|---|
| **Concept** (technology-agnostic) | "How should pagination work, and why?" | `docs/patterns/<NN-concern>/README.md` |
| **Implementation** (per stack) | "Show me working, tested pagination in Flutter / React / Django / FastAPI" | the four reference apps |

Each concept README links into the code for every stack, and each code module's
README links back to the concept. **The concept README is the entry point.**

## 2. Top-level layout

```text
.
├── CLAUDE.md                     # agent operating rules
├── SPECIFICATION.md              # requirements
├── README.md                     # how to navigate, run, and verify
├── Makefile                      # single quality-gate entry point (make check)
│
├── docs/
│   ├── architecture.md           # this file
│   ├── pattern-catalogue.md      # WHAT each pattern is (definitions, scope)
│   ├── cross-stack-matrix.md     # STATUS of each pattern per stack (single source of truth)
│   ├── implementation-roadmap.md # phases, dependencies, Definition of Done
│   ├── engineering-principles.md # SOLID/KISS/... with links to real code
│   ├── lifecycle.md              # idea → retirement (§55)
│   ├── adr/                      # architecture decision records
│   ├── patterns/NN-<concern>/    # concept READMEs + cross-stack comparison (§53)
│   └── common-problems/          # bad → why it fails → fix → test (§49)
│
├── contracts/
│   └── openapi.yaml              # shared HTTP contract (design-first)
│
├── flutter/reference_app/        # Flutter + Riverpod + Firebase demo app
├── react/reference_app/          # Vite + React + TypeScript demo app
├── django/reference_api/         # Django + DRF + Celery
├── fastapi/reference_api/        # FastAPI + SQLAlchemy 2 (async) + Alembic
├── firebase/                     # firebase.json, emulator config, security rules + rules tests
│
├── infrastructure/
│   ├── docker/                   # compose.yaml (dev), service Dockerfiles, nginx
│   └── deployment/               # deployment notes/manifests
├── .github/workflows/            # CI (must live here for GitHub to run it)
│
├── examples/<flow>/              # end-to-end cross-stack walkthroughs (see §6)
├── tests/
│   ├── contract/                 # both backends verified against contracts/openapi.yaml
│   └── e2e/                      # Playwright: React app against a real backend
└── scripts/                      # helper scripts called by the Makefile/CI
```

### Changes from the current skeleton and from SPECIFICATION §57

| Item | Decision | Why |
|---|---|---|
| `claude.md`, `specification.md` | Renamed to `CLAUDE.md`, `SPECIFICATION.md` (done) | `CLAUDE.md` references `SPECIFICATION.md`; on a case-sensitive filesystem the names must match, and Claude Code looks for `CLAUDE.md`. |
| `flutter/patterns/`, `react/patterns/`, `django/patterns/` (spec §57) | **Not created.** Patterns live as modules *inside* the reference apps. | A standalone snippet directory cannot be type-checked, tested, or run in context, so it rots. Code that lives in a real app is verified by the app's gates. |
| `common-problems/` (spec §49) | Docs in `docs/common-problems/`; code in a `common_problems` module inside each app | The bad and good versions need the real ORM, renderer, and test harness to show the failure (query counts, lost updates, rebuild counts). |
| `tests/` (top level) | Only **cross-stack** tests (contract, e2e) | Unit, widget, and API tests stay idiomatic and live with each stack. |
| `contracts/` | **Added** | Spec §42/§43 need one error model and one DTO set across stacks, and that needs a single source of truth. |
| `firebase/` | **Added** | Firestore/Storage security rules are authorization code and need their own tests. |
| `infrastructure/github-actions/` (spec §57) | Use `.github/workflows/` | GitHub only runs workflows from `.github/workflows/`. |
| `docs/engineering-principle.md` | Renamed to `engineering-principles.md` (done) | Matches spec §54 wording. |

## 3. The shared demonstration domain

The spec forbids building a product. The cross-stack comparisons only line up,
though, if every stack solves the *same* problem against the *same* data. The
fix is a deliberately small, neutral domain where **each entity exists to carry
specific patterns**:

| Entity | Exists to demonstrate |
|---|---|
| `User` (+ role: `user`, `manager`, `admin`, `superadmin`) | authentication, RBAC, account deletion, PII handling |
| `Post` (owner, status, soft-delete, `version`) | CRUD, ownership checks, pagination, full-text search, caching, optimistic locking |
| `Comment` | N+1 queries, nested resources, Firestore subcollections |
| `Attachment` | file upload, validation, signed URLs, storage adapters |
| `Product` / `Order` / `OrderItem` | transactions, `select_for_update`, inventory race conditions |
| `Wallet` / `LedgerEntry` | balance concurrency, append-only ledger, money handling |
| `Payment` / `ProviderTransaction` | payment state machine, provider adapters, reconciliation |
| `WebhookEvent` | signature verification, persistence, idempotent processing |
| `IdempotencyKey` | HTTP `Idempotency-Key` semantics |
| `OutboxEvent` | transactional outbox and the dual-write problem |
| `Device` / `Notification` | FCM token registry, invalidation, in-app notifications |
| `AuditLog` | auditing |

Rule: **an entity is added only when a pattern needs it.** No dashboards, no
business features.

## 4. Cross-stack contracts

### 4.1 HTTP contract (design-first)

`contracts/openapi.yaml` is the source of truth for the HTTP API.

- **Django and FastAPI both implement the same core contract.** Each backend's
  generated schema (drf-spectacular / FastAPI) is checked against it in CI, and
  `tests/contract/` runs property-based conformance tests (Schemathesis)
  against both running backends.
- **React** generates TypeScript types from it (`openapi-typescript`) and hand-writes
  a thin fetch client. Types are generated and behaviour is hand-written.
- **Flutter** hand-writes DTOs for clarity. Spec §43's "generate Dart types"
  is shown once as a documented alternative, not the default (see roadmap).
- Because both backends honour one contract, either client can point at either
  backend. That is the most direct demonstration of "same problem, different
  ecosystem".

### 4.2 Error model: RFC 9457 Problem Details

All backends return `application/problem+json`:

```json
{
  "type": "https://errors.reference.dev/validation-error",
  "title": "Validation failed",
  "status": 422,
  "code": "validation_error",
  "detail": "One or more fields are invalid.",
  "instance": "/api/v1/posts",
  "request_id": "01J9...",
  "errors": [{ "field": "title", "code": "required", "message": "This field is required." }]
}
```

| `code` | HTTP | Raised when |
|---|---|---|
| `bad_request` | 400 | malformed body or unparseable input |
| `validation_error` | 422 | well-formed input that violates rules (field errors in `errors[]`) |
| `authentication_error` | 401 | missing, invalid, or expired credentials |
| `authorization_error` | 403 | authenticated but not allowed |
| `not_found` | 404 | resource missing **or hidden for authorization reasons** |
| `method_not_allowed` | 405 | wrong HTTP method |
| `not_acceptable` | 406 | client cannot accept JSON |
| `unsupported_media_type` | 415 | request body is not JSON |
| `conflict` | 409 | version mismatch, duplicate, idempotency key in flight |
| `idempotency_key_reused` | 422 | same key, different payload |
| `rate_limited` | 429 | throttled (includes `Retry-After`) |
| `external_service_error` | 502/503 | provider failure |
| `internal_error` | 500 | unexpected error; never leaks internals |

Clients add errors that have no HTTP status: `network_error`, `timeout`,
`cancelled`, `parse_error`. Each client maps both families into **one sealed
error type** (Dart `sealed class AppError`, TS discriminated union `AppError`).
The state layer and UI then only ever see that type. Errors flow
**Backend → Problem JSON → API client → AppError → state → UI message**.

Django's default 400-for-validation and FastAPI's default 422 are both
overridden to this table. Making two frameworks agree is part of the lesson.

### 4.3 Other shared conventions

- **Pagination:** cursor (keyset) by default, `{ "items": [...], "next_cursor": "opaque" | null }`.
  Offset pagination `{ items, count, limit, offset }` only for admin-style tables.
- **Versioning:** URL prefix `/api/v1/`. The deprecation process is documented.
- **IDs:** UUIDv7 in public APIs, so client-visible IDs are not enumerable.
- **Money:** integer minor units plus ISO-4217 currency (`{ "amount": 1050, "currency": "KES" }`), never floats.
- **Time:** RFC 3339 UTC on the wire, converted to local time only in the UI.
- **Request IDs:** an `X-Request-ID` header is accepted or generated, logged everywhere, and returned in errors.
- **Auth:** `Authorization: Bearer <token>`, where the token is a first-party access token **or** a Firebase ID token (§5).

## 5. Authentication topology

Two real-world topologies are demonstrated, because both recur:

```text
A) Firebase-first (mobile default)
   Flutter ─ Firebase Auth ─▶ ID token ─▶ Django/FastAPI verifies with firebase-admin
                                          ─▶ maps uid → local User (created on first sight)
                                          ─▶ never trusts a client-sent user id

B) First-party (web default)
   React ─▶ POST /auth/login ─▶ short-lived access token (memory)
                              + rotating refresh token (httpOnly, Secure, SameSite cookie)
         ─▶ 401 → single-flight refresh → retry once → else logout
```

React also gets a **Firebase auth adapter** behind the same `AuthService`
interface. That is the one place an interface is clearly justified: two real
implementations exist. Django additionally shows session auth plus CSRF (the
Django-native way for same-site web apps).

## 6. Per-stack internal architecture

Each stack follows **its own ecosystem's idioms**. Layers are added only where
they remove real duplication or isolate a real dependency.

### Flutter: feature-first, layered inside features

```text
lib/
├── main.dart, app.dart
├── core/            # config, errors (AppError), networking (Dio client + interceptors),
│                    # logging, storage, routing (GoRouter), connectivity, theme, l10n
├── shared/          # reusable widgets (AsyncValueView, EmptyState, ...)
└── features/<feature>/
    ├── data/            # datasources (Firestore/REST), DTOs, repository implementations
    ├── domain/          # entities, repository contracts, use cases ONLY when orchestration exists
    ├── application/     # Riverpod Notifiers/AsyncNotifiers (controllers)
    └── presentation/    # screens + widgets (no Firebase/Dio imports, enforced by a lint/test)
```

This deviates from SPECIFICATION §4's global `data/ domain/` split. A global
split scatters each feature across the tree and does not scale. Feature-first
with layers inside is the common idiom for Riverpod apps, and §4 explicitly
allows adaptation. The data flow from §6, §8 and §10
(`UI → provider → controller → repository → data source → Firebase/API`) is
unchanged.

Riverpod 3 is used **without code generation** by default so the reference
stays readable. One feature shows the `@riverpod` generator for comparison.
`StateProvider`/`StateNotifier` are legacy in Riverpod 3 and are covered only in a
migration note, not as recommended patterns (this deviates from the §7 list on purpose).

The demo app is a **patterns catalogue app**: home lists categories, and each
screen demonstrates one pattern and links to its doc.

### React: Vite SPA, feature folders

```text
src/
├── app/             # providers, router, error boundary, layouts
├── lib/             # api client (fetch), AppError, query client, env, logger
├── shared/          # ui primitives, hooks (useDebounce, ...)
└── features/<feature>/
    ├── api.ts           # typed calls + TanStack Query hooks (query keys live here)
    ├── components/
    ├── routes/          # route modules (lazy-loaded)
    └── *.test.tsx
```

State categories follow §23: **local** (`useState`/`useReducer`), **server**
(TanStack Query), **form** (react-hook-form + zod), **URL** (search params),
**global client state** (Context for auth/theme). A global store library is
added only if a demo needs one, and that is currently not expected.

### Django: apps plus services/selectors

```text
reference_api/
├── config/          # settings.py (env-driven, 12-factor), urls, asgi/wsgi, celery
└── apps/
    ├── core/        # problem-details exception handler, pagination, request-id middleware,
    │                # logging, health endpoints
    ├── accounts/    # User, auth (session, token, Firebase), roles/permissions
    ├── posts/       # CRUD, search, caching, N+1 demos
    ├── files/       # uploads, storage backends, signed URLs
    ├── commerce/    # inventory, orders, wallet: transactions and locking
    ├── payments/    # state machine, providers/ (fake, stripe, mpesa, airtel), reconciliation
    ├── webhooks/    # receiver, verification, event store, async processing
    ├── notifications/  # email, FCM, in-app
    └── common_problems/
```

Within an app: `models.py`, `selectors.py` (read queries), `services.py`
(write use cases and transactions), `serializers.py` (I/O only), `views.py`
(HTTP only), `permissions.py`, `tasks.py`. These are plain functions, with no
`BaseService` or generic repository. The Django ORM already *is* the repository,
and §29 asks to show when an extra layer is justified. Payments are that case,
via provider adapters.

### FastAPI: feature modules plus dependency injection

```text
app/
├── core/            # settings (pydantic-settings), db (async SQLAlchemy session),
│                    # errors, logging, security, request-id middleware
└── <feature>/       # router.py, schemas.py (Pydantic DTOs), models.py (SQLAlchemy),
                     # service.py, dependencies.py
```

FastAPI's `Depends` is the DI system: auth, DB session, pagination params,
and permission checks are all dependencies. Alembic handles migrations.

## 7. Infrastructure and local environment

`infrastructure/docker/compose.yaml` provides the local services, each included
only because a pattern needs it. Phase 1 runs Postgres (host port 5433), Redis
(6380) and Mailpit (1025/8025); the others are added in the phase that needs
them. Ports are offset from the defaults so the stack can coexist with other
projects (full map in [01-foundations](patterns/01-foundations/README.md)).

| Service | Needed for |
|---|---|
| PostgreSQL 16 | both backends (tests run on real Postgres, never SQLite: locking, constraints, FTS) |
| Redis 7 | caching, Celery broker, rate limiting, pub/sub |
| Celery worker + beat | background jobs, schedules, reconciliation |
| Firebase Emulator Suite | Auth (email/Google/phone), Firestore, Storage, rules tests |
| MinIO | S3-compatible storage for signed-URL patterns |
| Mailpit | catching transactional email |
| stripe-mock | Stripe adapter tests without network |
| Nginx | reverse proxy and static/SPA serving (deployment phase) |

## 8. What cannot be fully verified locally

These are labelled explicitly in the matrix rather than marked complete:

| Area | Local verification | Needs real credentials or a device |
|---|---|---|
| Firebase Auth / Firestore / Storage | Emulator Suite + rules tests | production project config |
| FCM push, Crashlytics, Analytics | unit tests with fakes | real Firebase project + physical device |
| Google Sign-In (native) | emulator fake IdP | OAuth client IDs |
| Stripe | stripe-mock + signed webhook fixtures | test-mode keys |
| M-Pesa (Daraja), Airtel Money | recorded HTTP fixtures | sandbox credentials |
| Flutter integration tests | Chrome / Android emulator | iOS needs macOS |
