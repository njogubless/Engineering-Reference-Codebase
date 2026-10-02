# 0007 · Backend identity ships with the data layer (Phase 2), client auth in Phase 3

**Status:** Accepted (2026-10-02)

## Context
The roadmap put data and CRUD (Phase 2) before authentication (Phase 3). But
posts have authors, and both APIs deny by default. CRUD without identity
would have needed anonymous writes, a fake "user id" header (exactly the
trust-the-client mistake SPECIFICATION §30 warns against), or test-only
endpoints. Each would teach the wrong lesson.

## Decision
Phase 2 is split:
- **2a (backends):** user model, registration, login, rotating refresh tokens,
  logout, `/me`, then posts/comments CRUD with author-only writes and cursor pagination.
- **2b (clients):** data access and server state against those endpoints,
  using a minimal sign-in to exercise writes.

Phase 3 keeps everything client-side and federated: Firebase email, Google
and phone; backend Firebase ID-token verification; single-flight refresh;
secure storage; session restoration; account deletion.

## Consequences
- Every write endpoint is protected from the first commit that adds it.
- The custom user model exists before the first migration (Django's
  well-known "set AUTH_USER_MODEL first" rule).
- Phase 3 builds on working tokens instead of introducing them.
