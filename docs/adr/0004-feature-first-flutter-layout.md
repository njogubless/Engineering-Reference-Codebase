# 0004 · Feature-first Flutter layout, Riverpod 3 without codegen

**Status:** Accepted (2026-10-02)

## Decision
`lib/core/` holds cross-cutting code. Each feature has `data/`, `domain/`
(only when it has real rules), `application/` (providers/notifiers) and
`presentation/`. This deviates from SPECIFICATION §4's global `data/` and
`domain/` folders, as §4 allows. Providers are written without
`riverpod_generator` by default; one feature will show codegen for comparison.
`StateNotifier`/`StateProvider` are legacy in Riverpod 3 and appear only in a
migration note.

## Consequences
- Deleting or copying a feature is one folder.
- No abstract repository interface when there is one implementation and no
  domain rule (e.g. diagnostics); interfaces appear where two implementations
  exist (e.g. auth providers, payment adapters).

## Rejected
- Global layer folders: scatter each feature across the tree.
- Codegen everywhere: hides the provider model the reference is meant to teach.
