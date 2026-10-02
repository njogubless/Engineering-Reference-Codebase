# React reference app

Vite + React 19 + TypeScript (strict) + TanStack Query.

```bash
make -C ../.. setup-react
make -C ../.. run-react         # http://localhost:5410 → Django on :8410 by default
make -C ../.. check-react       # prettier, eslint (type-aware), tsc, vitest, build, API types
```

Point at FastAPI instead: `VITE_API_BASE_URL=http://localhost:8420` in `.env.local`.

| Path                        | What it demonstrates                                                                           |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| `src/lib/http.ts`           | typed `fetch` client: timeouts, cancellation, idempotent-only retries with jitter, request IDs |
| `src/lib/errors.ts`         | `AppError`, Problem type guard, exhaustive `userMessage`                                       |
| `src/lib/config.ts`         | validated public configuration (`VITE_*` is public!)                                           |
| `src/lib/api/schema.d.ts`   | types generated from the contract (`pnpm gen:api`)                                             |
| `src/app/providers.tsx`     | services through context; TanStack Query with retries off (one retry layer)                    |
| `src/app/ErrorBoundary.tsx` | render-error boundary; global capture in `main.tsx`                                            |
| `src/features/diagnostics/` | Phase 1 demo: config, flags, readiness, error handling end to end                              |

Tests use MSW, so the real `fetch` code path runs against mocked network responses.
