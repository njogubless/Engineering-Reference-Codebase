# Software Engineering Reference

Recurring engineering problems — authentication, pagination, error handling,
retries, caching, payments, webhooks, offline sync — solved idiomatically in
**Flutter/Dart**, **React/TypeScript**, **Django/Python** and **FastAPI/Python**,
with runnable code, tests and an explanation of the trade-offs.

This is not a product and not a template. It is a reference you return to
when a new project needs "the right way to do X".

## Find a pattern

1. Start with the concept: [docs/patterns/](docs/patterns/README.md). Each
   README explains the problem, when (not) to use the pattern, the trade-offs,
   common mistakes, and links to the code in every stack.
2. Check what exists: [docs/cross-stack-matrix.md](docs/cross-stack-matrix.md)
   is the status of every pattern in every stack.
3. Learn from failures: [docs/common-problems/](docs/common-problems/), bad →
   why it fails → fix → test.

| | |
|---|---|
| [docs/architecture.md](docs/architecture.md) | layout, shared domain, contracts, error model |
| [docs/pattern-catalogue.md](docs/pattern-catalogue.md) | what every pattern is |
| [docs/implementation-roadmap.md](docs/implementation-roadmap.md) | phases, dependency choices, Definition of Done |
| [docs/adr/](docs/adr/README.md) | decisions and what was rejected |
| [contracts/openapi.yaml](contracts/openapi.yaml) | the HTTP contract both backends implement |

## Layout

```text
contracts/          OpenAPI contract (source of truth for the HTTP API)
django/             Django + DRF reference API              → django/reference_api/README.md
fastapi/            FastAPI + SQLAlchemy reference API      → fastapi/reference_api/README.md
react/              React + TypeScript reference app        → react/reference_app/README.md
flutter/            Flutter + Riverpod reference app        → flutter/reference_app/README.md
infrastructure/     Docker Compose for local services
tests/contract/     verifies both backends against the contract
docs/               concepts, comparisons, decisions, status
```

## Run it

Requirements: Docker, Python 3.12, Node 22 + pnpm, Flutter 3.41.

```bash
make up        # Postgres :5433, Redis :6380, Mailpit :8025
make setup     # install all dependencies (hash-verified)
make check     # format, lint, types, tests, builds, contract — every stack

make run-django    # http://localhost:8410   (or run-fastapi → :8420)
make run-react     # http://localhost:5410
make run-flutter   # Chrome on :5420
```

Copy each project's `.env.example` to `.env` before running it locally.

## Status

Phase 1 (foundations) is implemented. See the [matrix](docs/cross-stack-matrix.md)
for exactly what is verified, and the [roadmap](docs/implementation-roadmap.md) for what is next.
