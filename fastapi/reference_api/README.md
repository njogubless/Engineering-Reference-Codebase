# FastAPI reference API

FastAPI + Pydantic v2 + SQLAlchemy 2 (async), implementing [contracts/openapi.yaml](../../contracts/openapi.yaml).

```bash
cp .env.example .env
make -C ../.. up setup-fastapi
make -C ../.. run-fastapi       # http://localhost:8420  (docs at /docs)
make -C ../.. check-fastapi     # format, lint, mypy --strict, tests
```

| Path | What it demonstrates |
|---|---|
| `app/main.py` | app factory, lifespan-managed clients, middleware order (CORS outermost) |
| `app/core/config.py` | typed `pydantic-settings`, fail-fast validation, typed feature flags |
| `app/core/errors.py` | Problem Details via per-type exception handlers; Pydantic → Django-compatible codes |
| `app/core/middleware.py` | pure-ASGI request context, unexpected-error handling, request logging |
| `app/health/router.py` | concurrent readiness checks with timeouts |

Compare with the Django API: same contract, same error codes, different
mechanics. See [docs/patterns/30-error-handling](../../docs/patterns/30-error-handling/README.md).
