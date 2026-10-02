from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        # Registers Django system checks (run by `manage.py check` and at startup).
        from apps.core import checks  # noqa: F401
