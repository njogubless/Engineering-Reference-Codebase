# Engineering Principles

Planned for Phase 19. Each principle (SOLID, DRY, KISS, YAGNI, separation of
concerns, composition over inheritance, dependency inversion, fail fast,
defensive programming, idempotency, immutability, explicit over implicit)
will link to working code that already applies it, rather than to standalone
examples. Early instances worth noting now:

- **Fail fast:** configuration validated at startup in every stack ([26-configuration](patterns/26-configuration/README.md)).
- **Explicit over implicit:** unknown feature flags raise; public endpoints opt out of auth explicitly.
- **YAGNI:** no repository interface for diagnostics (one implementation, no domain rules) — [ADR 0004](adr/0004-feature-first-flutter-layout.md).
