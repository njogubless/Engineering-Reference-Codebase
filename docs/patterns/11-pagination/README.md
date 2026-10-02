# 11 · Pagination

> Phase 2: cursor (keyset) pagination on the backends. Infinite scroll,
> pull-to-refresh and offset pagination for admin tables follow in Phase 6.

## The problem

`SELECT * FROM posts` works with 50 rows and takes the service down at 5
million. Offset pagination (`?page=200`) fixes the size problem but adds two more:
- `OFFSET 4000` makes the database read and throw away 4 000 rows, so deep
  pages get slower and slower;
- rows inserted while a user scrolls shift every later page: items repeat or vanish.

## The pattern: keyset with an opaque cursor

```sql
-- next page after the last row seen, (t, id), newest first
WHERE (created_at, id) < (:t, :id)
ORDER BY created_at DESC, id DESC
LIMIT :limit + 1            -- the extra row says whether another page exists
```

```json
{ "items": [ ... ], "next_cursor": "eyJ0IjogIjIwMjYtMTAt..." }   // null on the last page
```

- **A total order.** `created_at` alone isn't unique (the tests create five
  posts with one timestamp); `id` breaks ties.
- **An index in the same order:** a partial index
  `(created_at DESC, id DESC) WHERE status = 'published'`.
- **The cursor is opaque.** Clients pass it back unchanged and never build
  or parse it, which leaves the server free to change its format.
- **Limits are validated, not clamped.** `limit=500` is a 422, not quietly
  100 items. A client that asks for 500 should learn it gets 100 at most.
- **Tampered cursors are a 422** on the `cursor` field (DRF's default is a 404).

## How it is implemented

| | Django | FastAPI |
|---|---|---|
| Mechanism | DRF `CursorPagination`, customised ([apps/core/pagination.py](../../../django/reference_api/apps/core/pagination.py)) | hand-written keyset with a row comparison ([app/core/pagination.py](../../../fastapi/reference_api/app/core/pagination.py)) |
| Cursor content | DRF's position + offset (handles ties) | `{created_at, id}`, base64 JSON |
| Response shape | overridden to `{items, next_cursor}` | same |
| Queries per page | 1, asserted with `django_assert_num_queries` | 1, asserted by counting statements |

Both pass the same behavioural tests: walking every page returns every row
exactly once and in order, a row inserted mid-scroll doesn't duplicate or
shift anything, the last page has `next_cursor: null`, and invalid limits and
tampered cursors give 422s.

## When not to use cursors

When users need "jump to page 37" or a total count, as in admin tables, use
offset pagination with a capped page size and accept the trade-offs (Phase 6).

## Common mistakes

| ❌ | ✅ |
|---|---|
| Unbounded list endpoints | always paginate; cap `limit` |
| `ORDER BY created_at` alone | add a unique tiebreaker |
| Clients constructing cursors | opaque cursors |
| Silently clamping `limit` | reject out-of-range values |
| N+1 queries while rendering a page | eager-load authors (`select_related` / `joinedload`) and aggregate counts in the same query |
