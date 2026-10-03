# 06 · State Management

> Put each piece of state where it belongs. Most "state management problems"
> come from treating server data, form input, URL state and UI toggles as
> one kind of thing.

## The categories

| Kind | Example | Owner | React | Flutter |
|---|---|---|---|---|
| **Server state** | posts, the current user's profile | the server; the client holds a *cache* | TanStack Query | Riverpod `FutureProvider` / `AsyncNotifier` |
| **Session** | who is signed in | the client, synced from the server | `AuthProvider` + a tiny external store | `Notifier<Session?>` |
| **Local UI** | is a dialog open, a text field's value | one widget/component | `useState` | `StatefulWidget` / controller |
| **Form** | draft values, field errors, submitting | the form | `useState` now; react-hook-form in Phase 5 | controllers + local state |
| **URL** | current page, filters | the router | React Router (Phase 4/6) | go_router (Phase 4) |

A global store is not on the list. Neither app needs one yet, and both avoid it
until a real cross-tree, client-only state appears.

## Server state is a cache, not a copy

The rules in both apps:

- **Keys or providers identify data:** `postKeys.detail(id)` ↔ `postDetailProvider(id)`.
- **Mutations invalidate precisely:** creating a post marks the *lists* stale
  (where it lands is the server's decision), and seeds the detail cache so
  the next screen renders instantly.
- **Optimistic updates** follow a fixed sequence: cancel in-flight reads →
  snapshot → apply the change → send → on error restore the snapshot → re-sync
  from the server either way.
- **One retry layer:** the HTTP client retries, the cache library doesn't ([ADR 0005](../../adr/0005-single-retry-layer.md)).
- **Private data dies with the session:** sign-in and sign-out clear the
  cache (shared computers, drafts).

| | React (TanStack Query) | Flutter (Riverpod) |
|---|---|---|
| Paginated list | `useInfiniteQuery` + `getNextPageParam: page => page.next_cursor` | `AsyncNotifier<PostsListState>` with `loadMore()` |
| Load-more failure | the query's `error` + `fetchNextPage` again | a separate `loadMoreError` field: pages 1-2 stay on screen |
| Concurrent "load more" | guard it yourself (TanStack doesn't dedupe `fetchNextPage`): the button is disabled while `isFetchingNextPage` | `isLoadingMore` guard (tested: three calls, one request) |
| Optimistic edit | `onMutate` / `onError` / `onSettled` | `setStatus()`: replace, await, restore on `AppError` |
| Code | [features/posts/api.ts](../../../react/reference_app/src/features/posts/api.ts) | [posts_providers.dart](../../../flutter/reference_app/lib/features/posts/application/posts_providers.dart) |

Tests for optimistic behaviour were **mutation-checked**: disabling the
optimistic step makes them fail. An earlier version of the React delete test
passed without the feature (it observed the server's final state, not the
optimistic one) and was rewritten to inspect the cache while the request is
still pending.

## Riverpod: which provider, and why

Riverpod has many provider types. The reference uses each one only where its
specific property is needed:

| Provider | Used for | Why this one |
|---|---|---|
| `Provider` | `dioProvider`, `apiClientProvider`, `postsRepositoryProvider` | long-lived objects built synchronously; tests override them |
| `Provider` that throws unless overridden | `appConfigProvider` | values only `main()` knows; a missing override is a wiring bug and fails loudly |
| `FutureProvider.autoDispose` | diagnostics `serverMetaProvider` | read-only fetch, freed when the screen closes; `ref.onDispose` cancels the request |
| `FutureProvider.autoDispose.family` | `postDetailProvider(id)` | one cached fetch *per id* |
| `Notifier` | `sessionProvider` | synchronous state changed by methods (`signIn`, `signOut`, `expire`) |
| `AsyncNotifier` | `postsListProvider` | async initial load **plus** later changes (load more, refresh, optimistic edits): a `FutureProvider` cannot be changed after it resolves |
| `StreamProvider` | — (Phase 3, Firestore `watchPost`) | push-based data |
| Overrides | `ProviderScope(overrides: …)` in `main()` and tests; swapping the posts repository | the same screen runs against REST, Firestore or a fake |
| `ref.read` inside callbacks | the Dio auth interceptor reads the session at request time | `watch` would rebuild the HTTP client on every sign-in |
| `select` | `_PostTile` watches only `session.user.id` | a token refresh must not rebuild every row |

`StateProvider` and `StateNotifier` are legacy in Riverpod 3: use `Notifier`.
Riverpod 3 also *retries failing providers by default*, which is disabled in
`ProviderScope(retry: (_, _) => null)` (one retry layer).

## Common mistakes

| ❌ | ✅ |
|---|---|
| Copying server data into a global store, then syncing by hand | a server-state cache with keys and invalidation |
| `useEffect(() => fetch(...))` in components | query hooks (cancellation, caching, dedupe, states) |
| One `isLoading` for "first page" and "next page" | separate states: a failed page 3 must not blank pages 1-2 |
| Building new state from a snapshot taken before an `await` | build from the latest state (a real bug caught by a Flutter test: a stale error came back after a successful retry) |
| Keeping cached private data after sign-out | clear the cache on session change |
| Optimistic update without rollback | snapshot → apply → restore on error → re-sync |
