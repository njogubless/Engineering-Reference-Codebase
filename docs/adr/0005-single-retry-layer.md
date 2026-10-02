# 0005 · Retry in exactly one layer: the HTTP client

**Status:** Accepted (2026-10-02)

## Context
TanStack Query (3 retries by default), Riverpod 3 (automatic provider retry)
and the HTTP client can each retry. Stacked, they multiply: 3 × 3 = 9
requests per failure, a retry storm aimed at a server that is already struggling.

## Decision
The HTTP client retries transient failures of idempotent requests with
exponential backoff + full jitter, honouring `Retry-After`. TanStack Query
(`retry: false`) and Riverpod (`ProviderScope(retry: (_, _) => null)`) do not retry.

## Consequences
- Retry policy is defined and tested in one place per client.
- Probes and polling opt out per request (`retries: 0`).
