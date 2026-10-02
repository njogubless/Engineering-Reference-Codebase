# Django reference API

Django 5.2 LTS + Django REST Framework, implementing [contracts/openapi.yaml](../../contracts/openapi.yaml).

```bash
cp .env.example .env            # from this directory
make -C ../.. up setup-django   # services + dependencies
make -C ../.. run-django        # http://localhost:8410
make -C ../.. check-django      # format, lint, mypy --strict, checks, tests
```

| Path | What it demonstrates |
|---|---|
| `config/settings.py` | env-driven, fail-fast configuration; feature flags; CORS; secure defaults |
| `config/test_settings.py` | selecting `.env.test` for pytest/mypy |
| `apps/core/errors.py` | Problem Details for DRF, Django-native and unexpected errors |
| `apps/core/middleware.py`, `logging.py` | request IDs, structured JSON logs, redaction |
| `apps/core/views.py` | liveness/readiness probes, public `meta` endpoint |
| `apps/core/checks.py` | Django system check for configuration invariants |
| `apps/accounts/` | custom user model (email login, UUIDv7), registration, simplejwt tokens with rotation, `require_user` |
| `apps/posts/` | CRUD with selectors/services/permissions, DB constraints, partial indexes, `seed_demo` command |
| `apps/core/pagination.py` | DRF `CursorPagination` in the contract's shape, strict `limit`/`cursor` validation |
| `apps/core/serializers.py` | `StrictInputMixin`: unknown fields and type coercion rejected |
| `apps/common_problems/` | bad-vs-good demos with tests proving the difference |

Layering inside an app (introduced from Phase 2): `models.py`, `selectors.py`
(reads), `services.py` (writes and transactions), `serializers.py` (I/O),
`views.py` (HTTP). These are plain functions; no base classes.
