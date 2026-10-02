# 21 · Observability

> Phase 1 covers health probes and request IDs (see [31-logging](../31-logging/README.md)).
> Metrics, tracing and error tracking follow in Phase 15.

## Health checks: liveness vs readiness

Orchestrators (Kubernetes, ECS, load balancers) ask two different questions,
and confusing them causes outages.

| Probe | Question | On failure the platform... | Checks |
|---|---|---|---|
| **Liveness** `GET /health/live` | Is the process stuck? | **restarts** it | nothing external; if the code can answer, it is alive |
| **Readiness** `GET /health/ready` | Can it serve traffic right now? | **stops routing** to it (no restart) | the hard dependencies: database, Redis |

### Why liveness must not check the database

If the database goes down and liveness depends on it, the platform restarts
every API instance at once. That doesn't fix the database, it adds a
connection storm when the database comes back, and it turns a database outage
into a full API outage. Tested: the liveness test replaces the DB check with
one that explodes, and liveness still returns 200.

### Readiness rules

- Only **hard** dependencies. If the email provider is down, the instance can
  still serve most requests, so that check doesn't belong here.
- Every check has a **timeout** (2 s). A hanging dependency must produce
  "not ready", not a hanging probe (tested with a check that sleeps 10 s).
- FastAPI runs checks **concurrently** (`asyncio.gather`). Django runs them sequentially.
- The response is **public**, so it says only `ok`/`fail` per check. Details
  (hosts, credentials in DSNs, exception text) go to the logs (tested: a
  connection string containing a password never appears in the body).
- A broad `except Exception` is correct here and marked with a lint suppression.
  It's the one place where "any failure means not ready" is the requirement.

```json
// 200                                    // 503
{"status": "ok",                          {"status": "unavailable",
 "checks": {"database": "ok",              "checks": {"database": "ok",
            "redis": "ok"}}                           "redis": "fail"}}
```

| | Django | FastAPI |
|---|---|---|
| Code | [apps/core/views.py](../../../django/reference_api/apps/core/views.py) | [app/health/router.py](../../../fastapi/reference_api/app/health/router.py) |
| Shared clients | Django's connection handling; a short-lived Redis client per probe | engine + Redis client created in `lifespan`, closed on shutdown |
| Tests | [test_health.py](../../../django/reference_api/apps/core/tests/test_health.py) (real Postgres + Redis) | [test_health.py](../../../fastapi/reference_api/tests/test_health.py) (real Postgres + Redis) |

Clients treat readiness as data. A 503 here is an answer, not an error, so
the probe is fetched with `retries: 0` and `acceptStatuses: {503}` (see the
diagnostics demos).

## Coming in Phase 15

Error tracking (Sentry, Crashlytics), Prometheus metrics, OpenTelemetry
tracing across API → Celery, and analytics events.
