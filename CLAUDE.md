# Software Engineering Reference Repository

This repository is a cross-stack software engineering reference implementation:
recurring engineering problems solved idiomatically in Flutter/Dart,
React/TypeScript, Django/Python and FastAPI/Python, backed by PostgreSQL, Redis,
Firebase, Docker and CI/CD.

It is NOT a product application. Do not add business features.

## Read before making decisions

1. `SPECIFICATION.md` — requirements
2. `docs/architecture.md` — repository layout, shared domain, contracts, error model
3. `docs/pattern-catalogue.md` — what each pattern is (definitions)
4. `docs/cross-stack-matrix.md` — status of each pattern (single source of truth)
5. `docs/implementation-roadmap.md` — phases, dependency strategy, Definition of Done
6. `docs/adr/` — recorded decisions

## Rules

- Prefer idiomatic implementations for each ecosystem; do not force one
  architecture onto every stack.
- Do not create abstractions for their own sake (no `BaseService`,
  `AbstractBaseRepository`, `GenericManager`, ...). Every abstraction must solve
  a real recurring problem.
- Every dependency needs a reason recorded in the roadmap's dependency strategy.
- No placeholder implementations (`TODO`, `pass`, `UnimplementedError`,
  `return null`) in demonstrated code paths.
- Work phase by phase. Do not start a phase until the previous one passes
  `make check`.

## Before implementing a pattern

1. Check whether it already exists (catalogue + matrix + code).
2. Reuse existing abstractions where appropriate.
3. Implement, test, document (`docs/patterns/NN-*/README.md`), add a runnable example.
4. Run the stack's gate (`make check-<stack>`), then `make check`.
5. Update the catalogue and matrix in the same change.

## Completion tracking

The matrix is the source of truth for coverage. Never claim completion from
memory. A cell becomes ✅ only when every applicable Definition-of-Done gate in
`docs/implementation-roadmap.md` has been verified by running it; use 🧪 when
only emulators/fakes could verify it.

## Commands

- `make check` — every stack's format/lint/type/test/build gate
- `make check-flutter | check-react | check-django | check-fastapi | check-contract`
- `make up` / `make down` — local services (Postgres, Redis, Firebase emulators, Mailpit)
- Python: project venvs are created from `/usr/bin/python3` (the `python3` on
  PATH may be a virtualenv without pip).
