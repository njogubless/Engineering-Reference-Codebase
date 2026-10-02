# 01 · Foundations: repository conventions and the quality gate

> One command proves every stack is formatted, linted, type-checked, tested
> and buildable. CI runs the same command.

## The quality gate

| Gate | Django | FastAPI | React | Flutter | Contract |
|---|---|---|---|---|---|
| Format | `ruff format --check` | `ruff format --check` | `prettier --check` | `dart format --set-exit-if-changed` | – |
| Lint | `ruff check` (incl. bandit `S`, bugbear `B`, Django `DJ`) | `ruff check` (incl. `ASYNC`, `FAST`) | ESLint `strictTypeChecked` + react-hooks + jsx-a11y | `flutter analyze` (strict casts/inference/raw types) | Spectral |
| Types | `mypy --strict` + django-stubs | `mypy --strict` + pydantic plugin | `tsc -b` (`strict`, `noUncheckedIndexedAccess`) | analyzer | – |
| Tests | pytest on real Postgres + Redis | pytest on real Postgres + Redis | Vitest + Testing Library + MSW | `flutter test` | Schemathesis + drift tests |
| Build / sanity | `manage.py check`, `makemigrations --check` | – (no migrations yet) | `vite build`, generated types up to date | `flutter build web` | both backends boot |

```bash
make up       # Postgres, Redis, Mailpit
make setup    # all dependencies
make check    # everything above
```

Warnings are errors everywhere (`--max-warnings=0`, pytest `filterwarnings = error`,
Spectral `--fail-severity=warn`). A warning that is allowed to stay is
noise that hides the next real one.

## Dependency management

- **Every dependency is justified** in the roadmap's dependency table before it is added.
- **Lockfiles everywhere:** `requirements*.txt` with **hashes** (pip-tools,
  installed with `--require-hashes`, so a tampered package fails to install),
  `pnpm-lock.yaml` (`--frozen-lockfile` in CI), `pubspec.lock`.
- **Pinned toolchains:** Python 3.12, Node ≥ 22 (`engines`), Flutter 3.41.4 in
  CI, Dart SDK constraint in `pubspec.yaml`.
- **Updates:** Dependabot weekly, minor and patch grouped ([.github/dependabot.yml](../../../.github/dependabot.yml)).
- **Audit:** `pip-audit --require-hashes` and `pnpm audit --prod` in CI.

## Tests run against real infrastructure

Backend tests use the Postgres and Redis from `make up`, not SQLite or
in-memory fakes. Row locking, constraints, full-text search and transaction
semantics differ between databases, and later phases depend on them.
CI uses service containers on the same ports, so `.env.test` works unchanged.

## Port map

| Service | Port |
|---|---|
| Postgres (Docker) | 5433 |
| Redis (Docker) | 6380 |
| Mailpit SMTP / UI | 1025 / 8025 |
| Django dev / contract run | 8410 / 8411 |
| FastAPI dev / contract run | 8420 / 8421 |
| React dev | 5410 |
| Flutter web dev | 5420 |

Ports are offset from the defaults so this repository runs next to other projects.

## Notable toolchain findings

These were discovered while building Phase 1 and are kept as notes:
- **MSW 3** renamed `onUnhandledRequest` to `onUnhandledFrame`. With the old
  name, unhandled requests only warned and tests could silently hit nothing.
- **Starlette 1.x** deprecates `httpx` for `TestClient` in favour of `httpx2`.
- **pytest-django** loads settings before the root `conftest.py`, so test
  settings are selected via `config/test_settings.py`, not a conftest.
- **Riverpod 3** retries failed providers automatically, so it is disabled in
  `ProviderScope` (see [07-networking](../07-networking/README.md), one retry layer).
- **Vite's template** now ships oxlint. It was replaced with ESLint because
  type-aware rules (`no-floating-promises`, `no-unnecessary-condition`) need type information.
