"""Feature flags: typed, centrally declared, and loud about typos.

Flags live in `settings.FEATURES` (set from environment variables). Code asks
`is_enabled("search_v2")`; an unknown name raises instead of returning False,
because a misspelt flag that silently reads as "off" is a real production bug.

This is the simplest useful flag system. Move to a remote flag service only
when you need per-user targeting, gradual rollouts or runtime toggles.
"""

from django.conf import settings


class UnknownFeatureFlag(LookupError):
    pass


def is_enabled(name: str) -> bool:
    try:
        return settings.FEATURES[name]
    except KeyError:
        raise UnknownFeatureFlag(f"Unknown feature flag {name!r}") from None


def public_flags() -> dict[str, bool]:
    """Flags safe to expose to clients (GET /api/v1/meta)."""
    return {name: is_enabled(name) for name in settings.PUBLIC_FEATURES}
