# Architecture Decision Records

Short records of decisions that are expensive to reverse. Each says what was
decided, why, and what was rejected. Add one when a change affects more than
one stack or would surprise the next reader.

| # | Decision | Status |
|---|---|---|
| [0001](0001-design-first-contract-two-backends.md) | Design-first OpenAPI contract implemented by both backends | Accepted |
| [0002](0002-problem-details-error-model.md) | RFC 9457 Problem Details + one client error type | Accepted |
| [0003](0003-env-driven-fail-fast-configuration.md) | One env-driven settings module per stack, failing fast | Accepted |
| [0004](0004-feature-first-flutter-layout.md) | Feature-first Flutter layout, Riverpod 3 without codegen | Accepted |
| [0005](0005-single-retry-layer.md) | Retry in exactly one layer: the HTTP client | Accepted |
| [0006](0006-real-infrastructure-in-tests.md) | Backend tests run on real Postgres and Redis | Accepted |
| [0007](0007-backend-identity-before-crud.md) | Backend identity ships with the data layer; client auth in Phase 3 | Accepted |
