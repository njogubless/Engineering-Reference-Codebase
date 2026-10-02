# Common problem: swallowed exceptions

**Code:** [django/reference_api/apps/common_problems/swallowed_exceptions.py](../../django/reference_api/apps/common_problems/swallowed_exceptions.py)
**Tests:** [tests/test_swallowed_exceptions.py](../../django/reference_api/apps/common_problems/tests/test_swallowed_exceptions.py)

## ❌ Problematic implementation

```python
def convert_swallowing(amount, currency, provider):
    try:
        return amount * provider.get_rate(currency)
    except Exception:
        return None
```

## Why it fails

Three different failures, each needing a different response, collapse into one `None`:

| Failure | Correct outcome | What the bad version does |
|---|---|---|
| Unsupported currency (caller's fault) | 422 on the `currency` field | `None` |
| Provider down (nobody's fault) | 502, retry later, alert | `None`, nothing logged |
| Bug in our code (our fault) | 500, logged with traceback | `None`, bug invisible |

The tests prove each row: the outage and the user mistake return the same
value, a `TypeError` from our own code disappears, and nothing reaches the logs.

## ✅ Improved implementation

```python
def convert(amount, currency, provider):
    try:
        rate = provider.get_rate(currency)
    except KeyError:
        raise ValidationError({"currency": f"Unsupported currency {currency!r}."}, code="unsupported") from None
    except (ConnectionError, TimeoutError) as exc:
        raise ExternalServiceError("The exchange-rate provider is unavailable.") from exc
    return amount * rate
```

- Catch only the exceptions you can **name** and have a plan for.
- Translate them into the app's error model ([30-error-handling](../patterns/30-error-handling/README.md)).
- Chain with `from exc` so the logs keep the original cause.
- Let everything else propagate: the global handler logs it with the request
  ID and returns a 500 with no internals.

## The same mistake in other stacks

- **TypeScript:** `catch {}` or `.catch(() => [])` turns an outage into "no data". The React HTTP client never swallows: every failure becomes an `AppError`, and TanStack Query exposes it as `error`.
- **Dart:** `catchError((_) => null)` or `on Exception catch (_) {}`. `mapDioException` translates every case, and `toAppError` wraps unknowns instead of dropping them.

## When catching broadly *is* right

At a boundary that must report rather than fail, such as a readiness probe
deciding "ready or not". Even there the failure is logged, and a lint
suppression (`BLE001`) marks it as deliberate. See `apps/core/views.py`.
