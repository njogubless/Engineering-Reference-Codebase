"""Common problem: swallowed exceptions.

docs/common-problems/swallowed-exceptions.md explains the lesson; the tests in
tests/test_swallowed_exceptions.py prove each claim below.

Scenario: converting an amount with an exchange-rate provider. Three different
things can go wrong, and each needs a different response:

| Failure                     | Whose fault | Correct outcome                         |
|-----------------------------|-------------|-----------------------------------------|
| Unsupported currency        | the caller  | 422 validation_error, fixable by user   |
| Provider down / timing out  | nobody's    | 502 external_service_error, retry later |
| Bug in our code (TypeError) | ours        | 500 internal_error, logged, alerted     |
"""

from decimal import Decimal
from typing import Protocol

from django.core.exceptions import ValidationError

from apps.core.errors import ExternalServiceError


class RateProvider(Protocol):
    def get_rate(self, currency: str) -> Decimal:
        """Rate for `currency`.

        Raises KeyError if unsupported, ConnectionError/TimeoutError if the provider is down.
        """
        ...


# ❌ Problematic: every failure becomes `None`.
#
# - The caller cannot tell a user mistake from an outage, so it cannot pick a
#   status code, a message, or whether retrying makes sense.
# - Nothing is logged: an outage is invisible until users complain.
# - Bugs are hidden too: a TypeError in our own code looks like "no rate".
# - `None` travels on and fails later, far from the cause (or worse, is saved).
def convert_swallowing(amount: Decimal, currency: str, provider: RateProvider) -> Decimal | None:
    try:
        return amount * provider.get_rate(currency)
    except Exception:  # noqa: BLE001 - this is the anti-pattern being demonstrated
        return None


# ✅ Recommended: catch only what you can name, translate it into the app's
# error model, chain the cause, and let everything else propagate to the
# global handler (which logs it with the request ID and returns a 500).
def convert(amount: Decimal, currency: str, provider: RateProvider) -> Decimal:
    try:
        rate = provider.get_rate(currency)
    except KeyError:
        raise ValidationError(
            {"currency": f"Unsupported currency {currency!r}."}, code="unsupported"
        ) from None
    except (ConnectionError, TimeoutError) as exc:
        # `from exc` keeps the original traceback in the logs; the client only
        # sees the generic external_service_error.
        raise ExternalServiceError("The exchange-rate provider is unavailable.") from exc
    return amount * rate
