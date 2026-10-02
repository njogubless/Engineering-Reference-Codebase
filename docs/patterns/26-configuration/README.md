# 26 · Configuration

> Typed, validated, environment-driven configuration that fails at startup,
> never on the first request that needs a missing value.

## The problem

- Hard-coded URLs and credentials end up in git, and in every copy of the repo.
- `os.environ.get("DATABASE_URL", "sqlite://")` quietly runs production against
  the wrong database.
- A typo in an environment variable name is discovered at 3 a.m., on the first
  request that touches that code path.
- Per-environment code branches (`settings/prod.py` diverging from
  `settings/dev.py`) mean production runs code that was never tested.

## The pattern

1. **One code path, different values.** Each stack has one settings module.
   Environments differ only in values (12-factor).
2. **Required values have no default.** A missing value stops the process at startup.
3. **Defaults are the safe production values**: `DEBUG=false`, no allowed hosts, no CORS origins.
4. **Invariants are checked at startup**: `DEBUG` must be off in staging and
   production, `SECRET_KEY` must be strong there, CORS can't be `*` in production,
   production clients must use `https`.
5. **Every problem is reported at once**, not one per restart.
6. **Secrets live only on servers.** Anything compiled into a client
   (`VITE_*`, `--dart-define`) is public.

| Environment | Purpose | Values come from |
|---|---|---|
| `development` | local work | `.env` (copied from `.env.example`, git-ignored) |
| `test` | automated tests, CI | committed `.env.test` (no real secrets) |
| `staging` | production-like verification | the platform's secret store / CI variables |
| `production` | real users | the platform's secret store |

## How it is implemented

| | Django | FastAPI | React | Flutter |
|---|---|---|---|---|
| Mechanism | `django-environ` in one `settings.py` | `pydantic-settings` model | `import.meta.env` (Vite) | `--dart-define-from-file` |
| Fail-fast | `ImproperlyConfigured` at import | `ValidationError` on construction | `ConfigError` → error screen | `ConfigException` → error screen |
| Type safety | casts (`env.bool`, `env.list`, `env.db_url`) | type annotations, `Literal`, `PostgresDsn` | `AppConfig` interface + validation | `AppConfig` + `Environment` enum |
| Env-file override | `DJANGO_ENV_FILE` | `FASTAPI_ENV_FILE` | Vite modes (`.env.development`) | choose the JSON file |
| Feature flags | `settings.FEATURES` + `is_enabled()` that raises on unknown names | typed attributes (`settings.feature_search_v2`) | from `GET /api/v1/meta` | from `GET /api/v1/meta` |
| Code | [config/settings.py](../../../django/reference_api/config/settings.py), [apps/core/features.py](../../../django/reference_api/apps/core/features.py) | [app/core/config.py](../../../fastapi/reference_api/app/core/config.py) | [src/lib/config.ts](../../../react/reference_app/src/lib/config.ts) | [lib/core/config/app_config.dart](../../../flutter/reference_app/lib/core/config/app_config.dart) |

### What changes because of the ecosystem

- **Django** settings are a module of globals, so validation is plain `if`
  statements at import time, plus a **system check** (`core.E001`) for rules
  that span settings.
- **FastAPI** settings are a Pydantic model: types, ranges and cross-field
  validators come for free. A misspelt flag is a *type error* (`mypy`), where
  Django needs `is_enabled()` to raise at runtime.
- **Clients** can't keep secrets: Vite inlines `VITE_*` into the bundle, and
  `--dart-define` values can be extracted from the app binary.
- **Flutter** must call `String.fromEnvironment` with constant keys, so raw
  values are read in one factory and validated in `AppConfig.parse`.

## Feature flags

The simplest useful system: flags are declared in one place with typed
defaults and set from environment variables. Public flags reach clients
through `GET /api/v1/meta`, so clients don't need a rebuild to see a change.
Server-only flags are never exposed.

Move to a remote flag service only when you need per-user targeting, gradual
rollouts or changes without a deploy.

## Common mistakes

| ❌ Problematic | ✅ Recommended |
|---|---|
| `SECRET_KEY = "abc123"` in git | required environment variable; startup check for strength in deployed environments |
| `env.get("DATABASE_URL", "sqlite://")` | no default: missing means crash at startup |
| `settings/production.py` with different code | one module; environments differ in values |
| `DEBUG = True` as the default | safe defaults; `DEBUG` must be explicitly enabled, and is rejected in production |
| API keys in `VITE_*` or `--dart-define` | secrets stay on the server; clients call the server |
| `if (flags["serach_v2"])` silently false | unknown flag raises (Django) or fails type checking (FastAPI) |
| Committing `.env` | commit `.env.example` (documented, no values) and `.env.test` (test-only values) |
| `ENVIRONMENT=development  # comment` in a `.env` file | comments on their own line. django-environ keeps inline comments as part of the value (python-dotenv strips them, so the same file behaves differently per stack). Found while running Phase 1; the startup validation caught it immediately. |

## Edge cases covered by tests

Missing required values, invalid enum values, `DEBUG` in production, weak
`SECRET_KEY`, wildcard CORS in production, non-http(s) URLs, `http` in
production clients, comma-separated list parsing, undeclared public flags
(system check), and clients started with no configuration at all.
