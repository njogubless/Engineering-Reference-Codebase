from collections.abc import Mapping
from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail


class StrictInputMixin(serializers.Serializer):  # type: ignore[type-arg]
    """Make DRF input parsing as strict as the contract (and as Pydantic).

    DRF is lenient in two ways that hide client bugs:

    - **Unknown fields are silently dropped.** A typo like `tittle`
      "succeeds" and changes nothing, and `{"author": "<someone else>"}`
      invites mass-assignment mistakes. They are rejected as `unknown_field`.
    - **Numbers are coerced into strings.** `{"refresh": 0}` becomes `"0"`.
      String fields only accept JSON strings (`invalid`). Found by Schemathesis.

    All problems are reported together, so a client fixes them in one round trip.
    """

    def to_internal_value(self, data: Any) -> Any:
        errors: dict[str, Any] = {}
        if isinstance(data, Mapping):
            for name in sorted(set(data) - set(self.fields)):
                errors[name] = [ErrorDetail("Unknown field.", code="unknown_field")]
            for name, field in self.fields.items():
                raw = data.get(name)
                if (
                    isinstance(field, serializers.CharField)
                    and raw is not None
                    and not isinstance(raw, str)
                ):
                    errors[name] = [ErrorDetail("Not a valid string.", code="invalid")]
        try:
            result = super().to_internal_value(data)
        except serializers.ValidationError as exc:
            if not isinstance(exc.detail, dict):
                raise
            errors = {**exc.detail, **errors}
        if errors:
            raise serializers.ValidationError(errors)
        return result
