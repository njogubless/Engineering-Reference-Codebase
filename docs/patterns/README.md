# Patterns

Concept-first documentation. Each README explains the problem, the pattern,
when not to use it, trade-offs, common mistakes, tested edge cases, and how
each stack implements it. Numbers follow [the catalogue](../pattern-catalogue.md).

| # | Pattern | Stacks |
|---|---|---|
| 01 | [Foundations: conventions, quality gate, dependencies](01-foundations/README.md) | all |
| 03 | [Authentication: tokens, rotation, reuse detection](03-authentication/README.md) *(backend part)* | Django, FastAPI |
| 06 | [State management: server state, optimistic updates, Riverpod provider guide](06-state-management/README.md) | React, Flutter |
| 07 | [Networking: API client, timeouts, retries, cancellation](07-networking/README.md) | React, Flutter |
| 08 | [Data access: layers, DTO mapping, REST vs Firestore](08-data-access/README.md) | all |
| 09 | [Database: constraints, UUIDv7, timestamptz, migrations, indexes](09-database/README.md) | Django, FastAPI |
| 11 | [Pagination: keyset cursors](11-pagination/README.md) *(backend part)* | Django, FastAPI |
| 20 | [Security: secure defaults, CORS](20-security/README.md) *(Phase 1 part)* | Django, FastAPI |
| 21 | [Observability: health, liveness, readiness](21-observability/README.md) *(Phase 1 part)* | Django, FastAPI |
| 26 | [Configuration and feature flags](26-configuration/README.md) | all |
| 30 | [Error handling: Problem Details → AppError](30-error-handling/README.md) | all |
| 31 | [Logging and request IDs](31-logging/README.md) | all |
| 36 | [API contracts](36-api-contracts/README.md) | all |
| 41 | [Money, time and units](41-money-time/README.md) *(time)* | all |

Common problems: [swallowed exceptions](../common-problems/swallowed-exceptions.md) ·
[case-insensitive lookup that scans the whole table](../common-problems/case-insensitive-lookup-full-scan.md).
