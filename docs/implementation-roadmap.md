# Implementation Roadmap

> Status: **Phase 2a complete** (2026-10-02). Phase 2b (clients) is next.
> Status per pattern is tracked only in [cross-stack-matrix.md](cross-stack-matrix.md).

## Definition of Done

A matrix cell becomes ✅ only when **every applicable gate is verified by running it**.
A gate that does not apply is stated in the pattern's README, never silently skipped.

- [ ] Implementation is real code (no `TODO`, `pass`, `UnimplementedError`, or `return null` stand-ins in demonstrated paths)
- [ ] Tests cover the happy path, the failure paths, and the named edge cases
- [ ] Concept README in `docs/patterns/NN-*/` with: problem · when to use · when **not** to use · how it works · trade-offs · common mistakes · edge cases · per-stack comparison · how to adapt
- [ ] A runnable example (demo screen, endpoint, or `examples/` walkthrough)
- [ ] Errors map onto the shared error model
- [ ] Format, lint, and typecheck pass
- [ ] Build passes
- [ ] Catalogue and matrix updated in the same change

Cells verified only against emulators or fakes are marked 🧪, not ✅ (see architecture §8).

## Verification commands (the quality gate)

`make check` runs everything. `make check-<stack>` runs one stack. CI runs the same targets.

| Stack | Format | Lint | Types | Test | Build |
|---|---|---|---|---|---|
| Flutter | `dart format --set-exit-if-changed .` | `flutter analyze` | (analyzer, strict modes) | `flutter test`; `flutter test integration_test -d chrome` | `flutter build web` / `apk --debug` |
| React | `prettier --check` | `eslint` | `tsc --noEmit` | `vitest run`; `playwright test` | `vite build` |
| Django | `ruff format --check` | `ruff check` | `mypy --strict` (django-stubs) | `pytest` (real Postgres + Redis) | `manage.py check --fail-level WARNING`, `makemigrations --check` (`check --deploy` becomes gating in Phase 14) |
| FastAPI | `ruff format --check` | `ruff check` | `mypy --strict` | `pytest` (real Postgres + Redis) | `alembic check` (from Phase 2, when the first migration exists) |
| Firebase | – | – | – | rules tests on the emulator | – |
| Contract | – | Spectral lint of `openapi.yaml` | – | operation drift + Schemathesis + Problem shapes against both running backends | – |

## Dependency strategy

Principles:
1. Prefer the platform or framework built-in.
2. Add a library only when it is the ecosystem's established answer to a problem the repository actually demonstrates.
3. Every dependency is listed below with its reason, and lockfiles are committed.
4. Pin toolchains: `.tool-versions` / `.python-version`, `engines` in `package.json`, and `environment` in `pubspec.yaml`.

### Flutter (3.41 / Dart 3.11 installed)

| Dependency | Why | Rejected alternative |
|---|---|---|
| `flutter_riverpod` (3.x) | Spec requires Riverpod. No codegen by default (readability). | `riverpod_generator` everywhere: shown once for comparison |
| `go_router` | Official declarative router with redirects, shell routes, and deep links | auto_route (codegen) |
| `dio` | Interceptors, cancel tokens, upload/download progress | `http`: those features would need re-implementing |
| `firebase_core`, `firebase_auth`, `cloud_firestore`, `firebase_storage`, `firebase_messaging`, `firebase_crashlytics`, `firebase_analytics` | Spec §8 | – |
| `google_sign_in` | Spec §5 | – |
| `shared_preferences`, `flutter_secure_storage` | Preferences vs secrets (§15) | storing tokens in prefs (shown as the bad example) |
| `drift` + `sqlite3_flutter_libs` | Typed SQL for structured offline data and the sync queue | Hive (less actively maintained, no relational queries) |
| `connectivity_plus` | Connectivity signal (§18) | – |
| `image_picker`, `file_picker`, `cached_network_image` | §16, §19 | – |
| dev: `flutter_lints` (strict analysis options), `mocktail`, `fake_cloud_firestore`, `firebase_auth_mocks` | Tests without codegen or a network | mockito (codegen) |
| **Not used:** freezed / json_serializable | Dart 3 `sealed` classes + records cover unions, and DTOs are hand-written for clarity | revisit if DTO volume grows |

### React (Node 22, pnpm 11 installed)

| Dependency | Why | Rejected alternative |
|---|---|---|
| Vite, React 19, TypeScript (strict) | Plain SPA keeps routing, auth, and data fetching explicit | Next.js: RSC/SSR is a different topic; a note explains when to choose it |
| `react-router` (v7) | Nested layouts, loaders, lazy routes | TanStack Router (good, but less common) |
| `@tanstack/react-query` | The standard server-state cache (§23, §24); added in Phase 1 for the diagnostics demo | Redux Toolkit Query; a hand-rolled cache (shown as a bad example) |
| `react-hook-form` + `zod` + `@hookform/resolvers` | Uncontrolled forms (few re-renders); zod schemas give runtime validation and types | Formik |
| `@tanstack/react-virtual` | Virtualization (§27) | react-window |
| `firebase` (JS SDK) | Firebase auth adapter | – |
| `openapi-typescript` (dev) | Types from `contracts/openapi.yaml`; the client stays hand-written | full client generators |
| HTTP | **native `fetch` wrapper**, no axios | axios: unnecessary on modern runtimes |
| dev: ESLint (typescript-eslint strict, react-hooks, jsx-a11y), Prettier, Vitest, Testing Library, MSW 3, Playwright (Phase 17), `@axe-core/playwright` (Phase 16) | – | Jest (slower with Vite); oxlint (Vite's new default; no type-aware rules) |
| **Not used by default:** Zustand/Redux | Context covers auth and theme; added only if a demo needs cross-tree client state | – |

### Django (Python 3.12)

| Dependency | Why |
|---|---|
| Django 5.2 LTS, `djangorestframework` | Spec |
| `psycopg[binary]` 3 | PostgreSQL driver |
| `drf-spectacular` | OpenAPI generation, checked against the contract |
| `django-filter` | Whitelisted filtering (§12) |
| `django-environ` | Env-driven settings (§44) |
| `redis`, Django's built-in `RedisCache` | Cache backend (built-in since Django 4; no `django-redis` unless a feature needs it) |
| `celery[redis]` | Spec §35 |
| `firebase-admin` | ID-token verification, FCM sending |
| `django-storages[s3]` + `boto3` | S3/MinIO storage + presigned URLs |
| `argon2-cffi` | Argon2 password hasher |
| `stripe` | Stripe adapter (M-Pesa/Airtel use `httpx`: no maintained official SDKs) |
| `httpx` | Outbound HTTP with timeouts |
| `python-magic` | Content sniffing for uploads |
| `django-cors-headers` | CORS |
| `django-prometheus`, `sentry-sdk`, OpenTelemetry (phase 15) | Observability |
| dev: `pytest`, `pytest-django`, `factory_boy`, `ruff`, `mypy`, `django-stubs`, `djangorestframework-stubs`, `pip-audit` | Quality gate |

Environment management: `venv` + `pip-tools` (`requirements.in` → hashed `requirements.txt`). `uv` and Poetry are **not** installed on this machine. Switching to `uv` is one line in the Makefile if preferred.

### FastAPI (Python 3.12)

| Dependency | Why |
|---|---|
| `fastapi`, `uvicorn[standard]`, `pydantic` v2, `pydantic-settings` | Core |
| `sqlalchemy[asyncio]` 2.x + `asyncpg`, `alembic` | Async ORM + migrations (contrasts with Django's ORM) |
| `redis` (asyncio) | Caching, rate limiting, pub/sub |
| `firebase-admin`, `pyjwt`, `argon2-cffi` | Firebase verification, first-party JWTs, hashing |
| `httpx` | Outbound HTTP; also the test client |
| dev: `pytest`, `pytest-asyncio`, `httpx2` (Starlette 1.x `TestClient` transport), `ruff`, `mypy`, `pip-audit` | Quality gate |

FastAPI does **not** get a second job-queue library. It demonstrates `BackgroundTasks` and documents why durable jobs belong on a real queue (the Django/Celery reference).

### Platform

Docker Compose (Postgres 16, Redis 7, Mailpit now; Firebase emulators, MinIO, stripe-mock in their phases); GitHub Actions; Spectral (via `npx`); contract tests: `schemathesis`, `jsonschema-rs`, `pyyaml`, `httpx`, `pytest`; `@firebase/rules-unit-testing` (Phase 4); Dependabot; `osv-scanner` / Trivy (Phase 14).

## Phases

Dependencies flow downward: each phase uses only what earlier phases built.
Every phase ends with the full quality gate green, the matrix updated, and a
re-read of the relevant spec sections against what was built (§19 of the brief).

| # | Phase | Delivers (summary) | Depends on |
|---|---|---|---|
| **1** | **Foundations** | Repo hygiene (renames, git, README, Makefile, `.editorconfig`); four scaffolds with strict lint/type/test configs; Compose dev env; CI per stack; typed config + `.env.example` + fail-fast; Problem Details error model end to end (backend handlers, client `AppError`, UI mapping); structured logging + request IDs; health/live/ready; OpenAPI skeleton (Problem DTOs; Page DTOs moved to Phase 2 with the first list endpoint); CORS; client API clients (verbs, timeouts, cancel, error mapping, retry for idempotent methods); diagnostics demo screens; ADRs 0001–0006 | – |
| 2 | Data & state | Users/Posts/Comments models, constraints, indexes, migrations (both backends); CRUD per contract; contract tests; generated TS types; DTO mapping; Firestore CRUD/streams/transactions/batches/subcollections; Riverpod provider guide; async UI states; TanStack Query cache, invalidation, optimistic update; time handling | 1 |
| 3 | Authentication | Firebase email/Google/phone on the emulator (Flutter, React adapter); backend Firebase verification → local user; first-party auth with rotating refresh tokens; Django sessions + CSRF; single-flight refresh; secure storage; session restoration; account deletion | 2 |
| 4 | Authorization & routing | RBAC, object-level/ownership, 404-vs-403, admin; Firestore/Storage rules + tests; client permission state; GoRouter/React Router guards, nested routes, params, 404, shell navigation, deep links | 3 |
| 5 | Forms & validation | All §12/§26 forms; async + server validation → field errors; multi-step, dynamic, restoration; double-submit prevention | 4 |
| 6 | Lists | Offset + keyset pagination; infinite scroll; debounced race-free search; filtering/sorting; Postgres FTS/trigram; URL state; virtualization | 5 |
| 7 | Database depth & concurrency | N+1, annotations, soft delete, audit log, expand/contract migrations; `on_commit`; inventory and wallet races (concurrent tests); optimistic locking; `Idempotency-Key`; duplicate requests | 6 |
| 8 | Caching | Redis cache-aside, keys/TTL/versioning, invalidation, stampede, per-view pitfalls, ETag/Cache-Control, client cache policy, stale cache | 7 |
| 9 | Files | Validation, storage adapters (local/MinIO/Firebase Storage), presigned upload/download, deletion/orphans, client picker/progress/cancel/preview, thumbnail job | 4, 8 |
| 10 | Background jobs, email & events | Celery worker/beat, retries, idempotent tasks, dead-letter store, outbox, FastAPI BackgroundTasks contrast, transactional email via Mailpit | 7 |
| 11 | Webhooks & payments | Webhook receiver (signature, persist-then-ack, idempotency, ordering); payment state machine; Fake/Stripe/M-Pesa/Airtel adapters; double-payment prevention; reconciliation; money handling; client payment flows | 7, 10 |
| 12 | Notifications & real-time | FCM end to end (device registry, prune), notification deep links, in-app notifications; WebSockets + SSE + Redis pub/sub with reconnecting clients | 4, 10 |
| 13 | Offline & local storage | Prefs/secure/Drift; connectivity; cache-then-network; queued writes, sync, version-based conflicts | 2, 7 |
| 14 | Security hardening | Rate limiting, CORS/CSRF/headers/CSP, SQLi/XSS bad-vs-good, password policy and brute-force protection, secret scanning, dependency/container scanning, PII and data export | all prior |
| 15 | Observability | Sentry/Crashlytics, Prometheus metrics, OpenTelemetry tracing across API → Celery, analytics events, circuit breaker | 10 |
| 16 | Performance, a11y, i18n | Rebuild/render demos, leaks/disposal, isolates, images, bundle, streaming/compression; gen-l10n + React i18n, localized formatting; a11y + automated checks | 6 |
| 17 | Test depth | Flutter integration (Chrome/Android) + goldens; Playwright E2E; contract tests hardened in CI | all prior |
| 18 | Delivery | Production images, Nginx, deploy workflow, migrations on deploy, graceful shutdown, versioning/forced update | 17 |
| 19 | Synthesis docs + final audit | Design patterns and principles docs linked to real code; architecture styles; lifecycle; scalability; optional multi-tenancy; full audit against SPECIFICATION | all |

Common-problem (bad vs good) demos are built **inside the phase that owns the
concern** (N+1 in 7, retry storms in 10, double payments in 11, and so on), not deferred to the end.

### Phase 1: delivered

All gates verified on 2026-10-02 by `make check` (see the matrix for per-cell status):
Django 56 tests, FastAPI 35, React 58, Flutter 36, contract 12; lint, types, format and builds clean.

Deviations from the plan, each documented where it matters:
- `CursorPage`/`OffsetPage` removed from the contract until an endpoint uses them (Spectral flags unused components).
- CORS was pulled forward from Phase 14: browser demos cannot work without it.
- Secure transport settings (SSL redirect, secure cookies, X-Frame-Options) were pulled forward; HSTS stays opt-in.
- The Flutter home screen is the diagnostics demo. The pattern-catalogue navigation shell arrives with routing (Phase 4).
- Firebase is not used yet; it arrives with data access (Phase 2) and authentication (Phase 3).

### Phase 2a: delivered (backends + contract)

Reordered by [ADR 0007](adr/0007-backend-identity-before-crud.md): backend
identity ships with the data layer. Verified 2026-10-02 by `make check`
(Django 117 tests, FastAPI 88, contract 48).

- Custom user model (email login, UUIDv7), registration, login, rotating refresh
  tokens, idempotent logout, `/me`: simplejwt in Django, hand-written in FastAPI
  (hashed refresh tokens, family revocation on reuse, `FOR UPDATE` on rotation,
  timing-equalised login).
- Posts and comments CRUD with author-only writes, 404-vs-403 visibility,
  DB constraints, partial and composite indexes, cursor pagination
  (DRF `CursorPagination` vs hand-written keyset), one query per page.
- Alembic (async) with `alembic check` in the gate; migrations tested by the suite.
- Seed commands for demo data in both backends (`make seed`).
- Contract: auth and posts operations; authenticated Schemathesis on both backends.
  Its findings and fixes are listed in [36-api-contracts](patterns/36-api-contracts/README.md#what-the-contract-tests-found).

### Phase 2b (next): clients on real data

1. **React:** sign-in (email/password against the backend; access token in
   memory, refresh token handling kept minimal and replaced by the full
   architecture in Phase 3); a `posts` feature with TanStack Query (query-key
   factory, cursor `useInfiniteQuery`, create/edit/delete with invalidation,
   optimistic update + rollback), async UI states, local-time display.
2. **Flutter:** the same against the REST API: repository + DTO mapping,
   Riverpod provider guide (each provider type with its reason), paginated
   list, optimistic update. Firebase emulator setup with a Firestore data
   source (CRUD, streams, queries, transactions, batched writes,
   subcollections) behind a repository interface. That interface is
   justified here: two real implementations.
3. **Docs:** 06-state-management, 08-data-access, 41 time handling.
