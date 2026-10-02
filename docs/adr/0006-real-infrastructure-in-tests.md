# 0006 · Backend tests run on real Postgres and Redis

**Status:** Accepted (2026-10-02)

## Decision
Backend tests run against the Postgres and Redis started by `make up`
(Docker, ports 5433/6380). CI uses service containers on the same ports.
Fakes are used only for things that cannot run locally (payment providers,
FCM) or to force failures (readiness tests).

## Consequences
- Tests need Docker running locally.
- Locking, constraints, full-text search and transaction behaviour (Phases 6
  and 7) are tested as they will behave in production.

## Rejected
- SQLite for tests: no `select_for_update`, different constraint and FTS behaviour.
