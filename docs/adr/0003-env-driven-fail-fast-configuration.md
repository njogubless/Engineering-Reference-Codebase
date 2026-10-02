# 0003 · One env-driven settings module per stack, failing fast

**Status:** Accepted (2026-10-02)

## Decision
Each stack has one configuration module. Environments differ only in
values (12-factor). Required values have no defaults, defaults are the safe
production values, cross-setting invariants are validated at startup, and
all problems are reported at once. Tests use a committed `.env.test`, selected
by `DJANGO_ENV_FILE` / `FASTAPI_ENV_FILE` (Django via `config/test_settings.py`,
because pytest-django loads settings before conftest).

## Rejected
- `settings/{dev,prod}.py` hierarchies: production runs untested code paths.
- Defaults for required values: misconfiguration becomes silent misbehaviour.
