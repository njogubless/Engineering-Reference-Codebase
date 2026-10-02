# Software Engineering Pattern Catalogue

This file defines **what** each pattern is and its scope. **Status** lives only in
[cross-stack-matrix.md](cross-stack-matrix.md). Keeping definitions and status in one
place each prevents drift.

- **Stacks:** `F` Flutter · `R` React · `D` Django · `A` FastAPI · `P` platform (Firebase rules, Docker, CI, Postgres/Redis config) · `doc` documentation only
- **Phase:** see [implementation-roadmap.md](implementation-roadmap.md)
- **§:** section of SPECIFICATION.md that requires it. `+` marks an addition not in the spec.
- Categories 01–35 keep the spec's numbering. 36+ are additions.

---

## 01 · Foundations — P1
Repository conventions, toolchains, formatting/lint/type configs, Makefile quality gate, `.editorconfig`, README navigation. `F R D A P` · §56, §58

## 02 · Architecture — P1 (docs), applied throughout
- Layered vs clean vs feature-based architecture, with when each applies · `doc` + code links · §48
- Service layer, selectors/query layer, repository (when justified, when not) · `D A F` · §29, §48
- Modular monolith and microservice boundaries (concept + how the Django apps form modules) · `doc` · §48
- Event-driven concepts (domain events, outbox) → see 44 · §48
- Good abstraction vs over-engineering: side-by-side examples · `doc` + code · §51
- ADRs · `doc` +

## 03 · Authentication — P3
- Firebase email: register, login, logout, verify email, resend verification, forgot/reset/change password, delete account, session restore · `F R` · §5, §22
- Firebase Google: sign-in, new vs existing account, account linking, logout, restore, errors · `F R` · §5
- Firebase phone: entry, OTP send/verify/resend, timeout, invalid OTP, verification state · `F` (`R` where applicable) · §5
- Auth state machine: `Authenticated | Unauthenticated | Loading | Error | EmailVerificationRequired | PhoneVerification` · `F R` · §6
- Auth architecture: UI → provider → controller → repository → data source · `F R` · §6, §22
- Backend Firebase ID-token verification → local user mapping (never trust a client-sent uid) · `D A` · §30
- First-party auth: registration, login, logout, password reset, email verification · `D A` · §30
- Session auth + CSRF · `D` · §30
- Access/refresh tokens with rotation, reuse detection, revocation ("log out everywhere") · `D A R` · §22 +
- Token storage: memory + httpOnly cookie (web), secure storage (mobile); bad vs good · `R F` · §39
- Single-flight token refresh interceptor · `F R` · §10, §22
- OAuth/OIDC concepts (authorization code + PKCE) · `doc` · §30

## 04 · Authorization — P4
- Roles `user/manager/admin/superadmin`, RBAC permission map · `D A` · §31
- Object-level permissions and ownership checks · `D A` · §31
- Staff/admin access, Django admin hardening · `D` · §31
- 404 vs 403 to avoid resource enumeration · `D A` +
- Client permission state (hide or disable UI, never trust it) · `F R` · §22
- Firestore and Storage security rules + rules unit tests · `P` +
- Multi-tenant authorization → see 42

## 05 · Routing — P4
- Public, protected, auth guards/redirects, nested, path params, query params, unknown/404, modal routes, layouts, navigation state · `F R` · §9, §21
- Bottom navigation with preserved state (StatefulShellRoute) · `F` · §9
- Lazy route modules · `R` · §27
- Adapting the routing table to a real app · `doc` · §9

## 06 · State Management — P2 (introduced), deepened per phase
- Riverpod: Provider, FutureProvider, StreamProvider, Notifier, AsyncNotifier, family, autoDispose, dependencies, overrides (tests), each with a documented reason; legacy StateNotifier/StateProvider migration note · `F` · §7
- Async state shapes: loading, success, error, empty, refreshing, paginating · `F R` · §11, §24
- React categories: local, server (TanStack Query), form, URL, global (Context) · `R` · §23
- Optimistic updates with rollback · `F R` · §11, §24
- Connectivity state · `F` · §11

## 07 · Networking (API client) — P1 (core), P3 (auth interceptor)
- GET/POST/PUT/PATCH/DELETE through a typed client · `F R` · §10, §24
- Timeouts, cancellation, retries with exponential backoff + jitter (**idempotent methods only**) · `F R` · §10
- Interceptors: auth header, request ID, logging (redacted), token refresh · `F R` · §10
- Error mapping Problem JSON → `AppError` · `F R` · §10, §42
- Multipart upload with progress, download → see 14
- API client → remote data source → repository → (use case) → state → UI · `F R` · §10

## 08 · Data Access — P2
- Firestore: CRUD, streams, queries, filtering, ordering, pagination, transactions, batched writes, references, subcollections · `F` · §8
- Firestore → data source → repository → domain → Riverpod → UI · `F` · §8
- Remote vs local data sources, DTO ↔ entity mapping · `F R` · §10
- Server-state caching, invalidation, mutations · `R F` · §24
- Selectors and services (Django), async sessions (FastAPI) · `D A` · §29

## 09 · Database — P2 (models), P7 (depth)
- Models, relationships, constraints (unique, check, partial unique), indexes (B-tree, partial, GIN) · `D A` · §32
- Migrations: Django + Alembic; zero-downtime expand/contract; data backfills · `D A` · §32 +
- `select_related`/`prefetch_related` vs SQLAlchemy `selectinload`/`joinedload`; annotations, aggregations · `D A` · §32
- Soft deletion (manager/query filter + partial unique index) · `D A` · §32
- Query analysis: `EXPLAIN ANALYZE`, query-count assertions in tests · `D A` +
- Postgres connection pooling notes · `doc` +

## 10 · Forms & Validation — P5
- Login, registration, profile edit, password change, payment form, multi-step, dynamic fields, file field · `F R` · §12, §26
- Sync, async (e.g. username availability) and server validation → field errors · `F R` · §12, §26
- Submission state, double-submit prevention, focus/keyboard handling, form restoration · `F R` · §12
- Backend validation: serializers / Pydantic, cross-field rules · `D A` · §39

## 11 · Pagination — P6
- Offset, cursor/keyset (opaque cursors), stable ordering with a tiebreaker · `D A` · §32
- Infinite scroll, load more, pull to refresh, end-of-list, error-and-retry, duplicate prevention · `F R` · §13, §24
- Firestore cursor pagination (`startAfterDocument`) · `F` · §8
- Unbounded query (bad) vs max page size (good) · `D A` · §49

## 12 · Search, Filtering & Sorting — P6
- Debounce, cancel stale requests (race-free), local vs server search, search history, empty/loading/error · `F R` · §14
- Filtering/sorting via whitelisted params (django-filter / typed query deps) · `D A` · §14
- Postgres full-text search (`tsvector` + GIN), trigram similarity · `D A` +
- URL-synced filters · `R` · §23

## 13 · Caching — P8
- Cache-aside with Redis, TTL, key design and versioning · `D A` · §34
- Per-view caching and its pitfalls (per-user data) · `D` · §34
- Invalidation on write (`transaction.on_commit`), stampede protection · `D A` · §34 +
- HTTP caching: `ETag`/`If-None-Match`, `Cache-Control` · `D A` +
- Client caches: TanStack Query stale-time and invalidation, Riverpod keepAlive/cache-for, image caching · `R F` · §24
- Stale cache (bad vs good) · `common-problems` · §49

## 14 · File Storage — P9
- Upload validation: size, MIME by magic bytes, extension allowlist, image dimension limits · `D A` · §36, §39
- Storage abstraction: local, S3 (MinIO), Firebase Storage · `D A F` · §36
- Direct-to-storage uploads via presigned URLs; signed download URLs; deletion and orphan cleanup · `D A` · §36
- Picker, camera, gallery, multiple files, progress, cancellation, download, preview, client validation · `F R` · §16, §26
- Image processing in a background job (thumbnails) · `D` · §35

## 15 · Notifications — P12
- FCM: permission, token registration and refresh, foreground, background, tap → deep link, token invalidation · `F` · §17
- Backend device registry, sending via firebase-admin, pruning invalid tokens · `D A` · §17 +
- In-app notifications (persisted, read/unread) · `D R F` +
- Email notifications → see 40

## 16 · Background Processing — P10
- Celery + Redis: workers, beat schedules, retries with backoff, acks/visibility, time limits · `D` · §35
- Idempotent tasks; enqueue after commit (`on_commit`) · `D` · §35
- Failure handling: dead-letter table, alerting, manual replay · `D` · §35
- FastAPI `BackgroundTasks`: when in-process is acceptable and when it is not · `A` +
- Use cases: email, notifications, reports, image processing, third-party sync · §35

## 17 · Real-time — P12
- WebSockets (FastAPI native) with auth, heartbeats, reconnection with backoff · `A F R` +
- Server-Sent Events for one-way feeds · `A D R` +
- Fan-out with Redis pub/sub · `A` +
- Firestore realtime listeners vs your own socket · `F` + `doc`

## 18 · Payments — P11
- Lifecycle state machine: created → pending → processing → successful/failed/cancelled → refunded; illegal transitions rejected · `D A` · §38
- Provider adapters: Fake, Stripe, M-Pesa (Daraja STK Push), Airtel Money; business logic depends only on the port · `D` (`A` lighter) · §38
- Initiation with idempotency keys; double-payment prevention · `D A` · §38, §49
- Verification (never trust client "success"), persistence of provider transactions · `D` · §38
- Reconciliation job (provider vs ledger) · `D` · §38
- Client flows: initiate, poll/subscribe for status, handle pending · `F R` · §38

## 19 · Webhooks — P11
- Signature verification (HMAC, constant-time compare, timestamp tolerance) · `D A` · §37
- Persist-then-ack, async processing, idempotency by event ID, retries, failure handling · `D A` · §37
- Out-of-order events · `D` +
- Sending webhooks (outbound, signed, retried) · `doc` +

## 20 · Security — P14 (cross-cutting from P1)
- Input validation, SQL injection, XSS (bad vs good) · `D A R` · §39
- CSRF, CORS, secure headers/CSP, HSTS · `D A P` · §39
- Rate limiting: DRF throttles, Redis token bucket · `D A` · §39
- Password hashing (Argon2), password policy, brute-force protection · `D A` · §39
- Secrets management, secret scanning · `P` · §39, §44
- Dependency and container scanning · `P` · §45
- SSRF and open-redirect notes · `doc` +

## 21 · Observability — P1 (logging, request IDs, health), P15 (metrics, tracing)
- Health, liveness, readiness (dependency checks) · `D A P` · §40
- Request IDs propagated client → server → worker · `F R D A` · §40
- Error tracking (Sentry for backends/React, Crashlytics for Flutter) · `F R D A` · §40
- Metrics (Prometheus), tracing (OpenTelemetry) · `D A` · §40
- What to log and what never to log (tokens, passwords, PII) · `doc` · §40

## 22 · Testing — every phase; P17 for E2E/contract depth
- Flutter: unit, widget, integration (`integration_test`), golden where appropriate · `F` · §41
- React: unit, component (Testing Library), integration (MSW), E2E (Playwright) · `R` · §41
- Django: unit, model, service, API, permission, authentication, integration (pytest-django, factory_boy) · `D` · §41
- FastAPI: pytest + httpx AsyncClient, dependency overrides, transactional test DB · `A` · §41
- Contract tests against `contracts/openapi.yaml` · `P` +
- Test data factories, fakes vs mocks (and when to use each) · `doc` +

## 23 · Performance — P16 (plus common problems throughout)
- Flutter: const, lazy lists, rebuild scoping (`select`), isolates, image cache/resize, controller disposal, debouncing · `F` · §19
- React: memoization (when it helps), lazy/code-splitting, virtualization, debounce/throttle, image optimization, bundle analysis · `R` · §27
- Backend: N+1, indexes, pagination, payload size, streaming responses, compression · `D A` · §32, §49

## 24 · Offline — P13
- Connectivity detection (and why it is not offline support) · `F` · §18
- Cache-then-network reads, offline UI, queued writes (local outbox), retry/sync, conflict resolution (version-based) · `F` · §18
- Firestore offline persistence vs custom sync: when each fits · `F` `doc` · §18

## 25 · Local Storage — P13
- SharedPreferences (prefs), flutter_secure_storage (secrets), Drift/SQLite (structured offline data), each with its justification · `F` · §15
- Web: what belongs in localStorage and what never does · `R` +

## 26 · Configuration — P1
- Env-driven typed settings: dev, test, staging, prod; `.env` + `.env.example`; fail fast on missing config · `F R D A` · §44
- Flutter flavors / `--dart-define`, Vite env, Firebase config per environment · `F R` · §44
- Feature flags (simple typed flags, then remote config) · `F R D` · §44
- Never commit secrets (bad vs good) · `doc` · §44

## 27 · Internationalization & Localization — P16
- Flutter `gen-l10n` (ARB), React i18n, pluralization, RTL · `F R` · +
- Locale-aware number/date/currency formatting · `F R` +
- Backend translation of error messages (or stable codes + client translation; decision documented) · `D A` +

## 28 · Accessibility — P16
- Semantics, focus order, touch targets, contrast, screen-reader labels · `F R` +
- Automated checks: `eslint-plugin-jsx-a11y`, axe in tests, Flutter semantics tests · `F R` +

## 29 · Deep Linking — P4 (routing), P12 (notifications)
- App Links / Universal Links config, GoRouter deep links, notification-tap routing, auth-gated deep links (resume after login) · `F R` · §9, §17

## 30 · Error Handling — P1
- One error taxonomy across stacks (see architecture §4.2) · `F R D A` · §42
- Backend exception handlers → Problem JSON · `D A` · §42
- Client `AppError` sealed type; error → state → UI message mapping · `F R` · §42
- Error boundaries (React), `FlutterError.onError` / `PlatformDispatcher.onError` · `F R` +
- Swallowed exceptions (bad vs good) · `common-problems` · §49

## 31 · Logging — P1
- Structured JSON logs, levels, context (request ID, user ID), redaction · `D A` · §40
- Client logging with levels and sinks; nothing sensitive · `F R` · §40

## 32 · CI/CD — P1 (gates), P18 (deploy)
- Per-stack workflows with path filters: format, lint, typecheck, test, build · `P` · §45
- Docker build, security scanning, deployment workflow, environments and approvals · `P` · §45

## 33 · DevOps — P1 (compose), P18 (prod images)
- Compose for local dev; multi-stage, non-root production images for Django, Celery, React+Nginx · `P` · §46
- Migrations during deploy, graceful shutdown, zero-downtime notes · `P` +

## 34 · Documentation — every phase
- Per-pattern README (problem, when, how, trade-offs, mistakes, adaptation) · §50
- Cross-stack comparison per concern (what stays the same, what changes, trade-offs) · §53
- Software lifecycle (idea → retirement) · §55
- OpenAPI docs served by both backends · §43

## 35 · Scalability — P15/P19 (mostly docs)
- Stateless app servers, horizontal scaling, sticky-session pitfalls (WebSockets) · `doc`
- Read replicas, connection pooling (PgBouncer), queue-based load leveling · `doc`
- Partitioning and archival concepts · `doc`

---

## Additions beyond the spec's category list

## 36 · API Contracts & Versioning — P1 (skeleton), P2 (resources)
- Design-first OpenAPI; request/response/error/pagination DTOs; auth schemes · `P D A` · §43
- Generated TypeScript types; Dart generation as a documented alternative · `R F` · §43
- `/api/v1` versioning, deprecation headers, backwards-compatible change rules · `D A` · §28, §43

## 37 · Concurrency & Transactions — P7
- `atomic`, transaction boundaries (bad: side effects inside, good: `on_commit`) · `D A` · §33
- Pessimistic locking `select_for_update` (inventory, wallet) · `D A` · §33
- Optimistic locking (`version` column, `ETag`/`If-Match` → 409) · `D A F R` +
- Lost updates and check-then-act races (bad vs good, with concurrent tests) · `D A` · §33, §49
- Distributed locks in Redis and their limits · `D` +

## 38 · Idempotency — P7
- HTTP `Idempotency-Key` middleware/dependency: store, replay, in-flight 409, payload mismatch 422 · `D A` · §33, §38
- Client generates the key once per user intent · `F R` +
- Unique constraints as the final guard · `D A` +

## 39 · Resilience — P1 (client), P10/P11 (backend)
- Timeouts everywhere, retry with backoff + jitter, retry budgets, circuit breaker for providers · `F R D A` · §49
- Partial failure and compensation (saga-lite) · `D` · §49
- Retry storms (bad vs good) · `common-problems` · §49
- Graceful degradation · `doc` +

## 40 · Email — P10
- Transactional email via a task, templates (HTML + text), Mailpit in dev, provider adapter · `D` (`A` lighter) · §28, §35

## 41 · Money, Time & Units — P11 (money), P2 (time)
- Money as integer minor units + currency; `Decimal`; rounding rules; formatting · `F R D A` +
- UTC storage, timezone conversion at the edge, DST pitfalls, date-only vs instant · `F R D A` +

## 42 · Multi-Tenancy — P19 (optional)
- Tenant-scoped queries, tenant from token, row-level isolation, cross-tenant leak tests · `D A` +

## 43 · Auditing, Privacy & Data Lifecycle — P7, P14
- Audit log (who/what/when/before/after) · `D` · §32
- PII minimization, account deletion and data export, retention · `D F` · §5 +

## 44 · Events & Messaging — P10
- Domain events, transactional outbox, at-least-once delivery and consumer idempotency · `D` · §48 +

## 45 · Design Patterns (applied) — P19 (docs over real code)
Repository, Service, Factory, Strategy, Adapter, Observer, DI, State, Command, Builder, Facade, Decorator. Each links to **where the pattern already exists in the codebase** (e.g. Adapter → payment providers, State → payment lifecycle, Decorator → retry, Observer → streams) with problem / why it helps / when not to use it. No contrived standalone examples. · §47

## 46 · Engineering Principles — P19
SOLID, DRY, KISS, YAGNI, separation of concerns, composition over inheritance, DIP, SRP, fail fast, defensive programming, idempotency, immutability, explicit over implicit. Each has a small working example plus links to real code. · §54

## 47 · Software Lifecycle — P19
Idea → requirements → architecture → data modelling → API contract → implementation → testing → CI → deployment → monitoring → maintenance → refactoring → retirement, with the practices and artifacts of each stage. · §55

## 48 · Common Problems — accumulated in each phase
Bad → why it fails → improved → test, for: N+1 queries, race conditions, duplicate requests, double payments, memory leaks, unnecessary Flutter rebuilds, unnecessary React renders, stale cache, token expiration, network timeout, partial failure, retry storms, large payloads, slow images, large lists, unvalidated input, authorization bugs, swallowed exceptions, insecure token storage, side effects inside transactions, retrying non-idempotent requests. · §49

## 49 · Dependency Management — P1
Lockfiles for every stack, pinned toolchain versions, Renovate/Dependabot, `pip-audit` / `npm audit` / `osv-scanner`, licence awareness. · §56 +

## 50 · App Lifecycle & Release (mobile/web) — P18
Flutter app lifecycle (resume/pause), versioning, forced/optional update, release channels, web cache busting. · +
