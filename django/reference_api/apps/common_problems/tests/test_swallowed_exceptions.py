from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.common_problems.swallowed_exceptions import convert, convert_swallowing
from apps.core.errors import ExternalServiceError


class FakeProvider:
    def __init__(self, failure: Exception | None = None, rate: object = Decimal("2")) -> None:
        self.failure = failure
        self.rate = rate

    def get_rate(self, currency: str) -> Decimal:
        if self.failure is not None:
            raise self.failure
        if currency != "KES":
            raise KeyError(currency)
        return self.rate  # type: ignore[return-value]


class TestSwallowing:
    def test_different_failures_become_indistinguishable(self):
        unsupported = convert_swallowing(Decimal(10), "XYZ", FakeProvider())
        outage = convert_swallowing(Decimal(10), "KES", FakeProvider(ConnectionError("down")))
        assert unsupported is None
        assert outage is None  # same result: the caller cannot react correctly

    def test_bugs_are_hidden_too(self):
        # A provider returning a string is a bug in our integration; it vanishes.
        assert convert_swallowing(Decimal(10), "KES", FakeProvider(rate="2")) is None

    def test_nothing_is_logged(self, caplog):
        convert_swallowing(Decimal(10), "KES", FakeProvider(ConnectionError("down")))
        assert caplog.records == []


class TestTranslating:
    def test_success(self):
        assert convert(Decimal(10), "KES", FakeProvider()) == Decimal(20)

    def test_caller_mistake_is_a_validation_error_on_the_field(self):
        with pytest.raises(ValidationError) as info:
            convert(Decimal(10), "XYZ", FakeProvider())
        assert info.value.message_dict == {"currency": ["Unsupported currency 'XYZ'."]}

    @pytest.mark.parametrize("failure", [ConnectionError("down"), TimeoutError("slow")])
    def test_outage_is_an_external_service_error_with_the_cause_chained(self, failure):
        with pytest.raises(ExternalServiceError) as info:
            convert(Decimal(10), "KES", FakeProvider(failure))
        assert info.value.__cause__ is failure

    def test_bugs_propagate(self):
        with pytest.raises(TypeError):
            convert(Decimal(10), "KES", FakeProvider(rate="2"))
