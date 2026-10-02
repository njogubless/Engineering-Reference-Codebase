import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings

REQUIRED = {
    "database_url": "postgresql://u:p@localhost:5433/db",
    "redis_url": "redis://localhost:6380/0",
}


def test_meta_exposes_only_public_flags(client: TestClient):
    assert client.get("/api/v1/meta").json() == {
        "api_version": "1",
        "environment": "test",
        "features": {"maintenance_banner": True},
    }


def make_settings(**values: object) -> Settings:
    # _env_file=None: only the values passed here (and real env vars) count.
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_valid_production_settings():
    settings = make_settings(environment="production", **REQUIRED)
    assert settings.debug is False
    assert settings.async_database_url.startswith("postgresql+asyncpg://")


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"environment": "production"}, "database_url"),
        ({"environment": "prod", **REQUIRED}, "environment"),
        ({"environment": "production", "debug": True, **REQUIRED}, "DEBUG must be off"),
        ({"environment": "test", "readiness_timeout_seconds": 0, **REQUIRED}, "greater than 0"),
        (
            {"environment": "production", "cors_allowed_origins": "*", **REQUIRED},
            "explicit origins",
        ),
    ],
)
def test_invalid_settings_fail_at_startup(values: dict[str, object], message: str):
    with pytest.raises(ValidationError, match=message):
        make_settings(**values)


def test_cors_origins_parse_from_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a.test, http://b.test")
    settings = make_settings(environment="test", **REQUIRED)
    assert settings.cors_allowed_origins == ["http://a.test", "http://b.test"]
