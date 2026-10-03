# 08 · Data Access

> How data travels from storage to the screen, and which layers are worth
> having in each stack.

## Layers, and when each earns its place

```text
Backend (Django)      view ─► serializer ─► service / selector ─► ORM ─► PostgreSQL
Backend (FastAPI)     router ─► Pydantic schema ─► service ─► SQLAlchemy (async) ─► PostgreSQL
React                 component ─► query hook (features/x/api.ts) ─► HTTP client ─► API
Flutter               widget ─► provider/notifier ─► repository ─► API client / Firestore
```

| Layer | Exists because | Not added where |
|---|---|---|
| Django selectors/services | views stay HTTP-only; queries and use cases are reusable and testable | no repository over the ORM: the ORM already *is* one |
| FastAPI service module | owns the transaction (explicit `commit`) and the visibility rules | no generic `BaseRepository` |
| React `api.ts` per feature | query keys, cache updates and types in one place per feature | no `ApiService` class wrapping the client |
| Flutter repository **interface** | two real implementations: REST and Firestore | diagnostics has a concrete repository and no interface (one implementation) |
| DTO mapping | the wire format and the domain differ (`display_name` vs `authorName`, ISO strings vs `DateTime`); validation happens at the boundary | — |

## Mapping at the boundary

- **Flutter** parses JSON with Dart 3 patterns into immutable entities and
  rejects bad shapes as `ParseError` ([post_dto.dart](../../../flutter/reference_app/lib/features/posts/data/post_dto.dart)).
  Timestamps without a UTC designator are rejected outright.
- **React** uses types generated from the contract; runtime validation of
  responses (zod) comes with forms in Phase 5.
- **Django** serializers are I/O only, split into read and write
  serializers. **FastAPI** uses Pydantic models with `extra="forbid"` for input.

## One interface, REST and Firestore

`PostsRepository` has two implementations. The same `PostsListController`
and `PostsScreen` run against either, by overriding `postsRepositoryProvider`.

| Concern | REST | Firestore |
|---|---|---|
| Joins | the API embeds the author | **denormalise**: copy `authorName` into each post |
| Counts | aggregated by the server per request | **maintained**: `commentCount` updated in a transaction with each new comment |
| Deleting a parent | `ON DELETE CASCADE` | **no cascade**: delete the `comments` subcollection in the same batch (≤ 500 writes per batch) |
| Pagination | opaque server cursor | `startAfterDocument`, which adds the document id as an implicit tiebreaker |
| Timestamps | server clock via the API | `FieldValue.serverTimestamp()`: **null in local snapshots until confirmed**; one-off reads use `ServerTimestampBehavior.estimate`, streams fall back to "now" |
| Live updates | refetch / invalidate | `snapshots()` streams (`watchPost`) |
| Atomic multi-writes | a database transaction | `runTransaction` (its function may be retried: no side effects) or `batch()` |
| Errors | Problem Details → `AppError` | `FirebaseException` codes → `AppError` (`_guard`) |
| Authorization | server permissions | **security rules** (Phase 4); the repository cannot enforce anything |

**Verification status (🧪):** the Firestore repository is tested against
`fake_cloud_firestore`. Two limitations of the fake are documented in its
tests: it can't use `FieldPath.documentId` in cursors, and its tiebreak
direction differs from Firestore's. Running against the emulator arrives
with Firebase Auth in Phase 3, because writes need authenticated security rules.
