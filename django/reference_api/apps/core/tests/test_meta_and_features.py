import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError
from rest_framework.test import APIClient

from apps.core.features import UnknownFeatureFlag, is_enabled


def test_meta_exposes_only_public_flags():
    response = APIClient().get("/api/v1/meta")
    assert response.status_code == 200
    assert response.json() == {
        "api_version": "1",
        "environment": "test",
        "features": {"maintenance_banner": True},  # search_v2 is server-only
    }


def test_unknown_flag_raises_instead_of_reading_as_off():
    with pytest.raises(UnknownFeatureFlag):
        is_enabled("serach_v2")


def test_system_check_rejects_undeclared_public_flags(settings):
    settings.PUBLIC_FEATURES = ("maintenance_banner", "ghost_flag")
    with pytest.raises(SystemCheckError, match="ghost_flag"):
        call_command("check")


def test_openapi_schema_is_public():
    assert APIClient().get("/api/schema").status_code == 200
