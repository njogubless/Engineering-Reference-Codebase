# Patterns

Concept-first documentation. Each README explains the problem, the pattern,
when not to use it, trade-offs, common mistakes, tested edge cases, and how
each stack implements it. Numbers follow [the catalogue](../pattern-catalogue.md).

| # | Pattern | Stacks |
|---|---|---|
| 01 | [Foundations: conventions, quality gate, dependencies](01-foundations/README.md) | all |
| 07 | [Networking: API client, timeouts, retries, cancellation](07-networking/README.md) | React, Flutter |
| 20 | [Security: secure defaults, CORS](20-security/README.md) *(Phase 1 part)* | Django, FastAPI |
| 21 | [Observability: health, liveness, readiness](21-observability/README.md) *(Phase 1 part)* | Django, FastAPI |
| 26 | [Configuration and feature flags](26-configuration/README.md) | all |
| 30 | [Error handling: Problem Details → AppError](30-error-handling/README.md) | all |
| 31 | [Logging and request IDs](31-logging/README.md) | all |
| 36 | [API contracts](36-api-contracts/README.md) | all |

Common problems: [swallowed exceptions](../common-problems/swallowed-exceptions.md).
