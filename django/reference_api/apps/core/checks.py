"""Django system checks: configuration mistakes fail at startup, not in production traffic."""

from typing import Any

from django.conf import settings
from django.core.checks import CheckMessage, Error, register


@register()
def check_public_features(app_configs: Any, **kwargs: Any) -> list[CheckMessage]:
    unknown = set(settings.PUBLIC_FEATURES) - set(settings.FEATURES)
    return (
        [
            Error(
                f"PUBLIC_FEATURES lists undeclared flags: {sorted(unknown)}",
                hint="Declare every flag in settings.FEATURES.",
                id="core.E001",
            )
        ]
        if unknown
        else []
    )
