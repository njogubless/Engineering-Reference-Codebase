import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings

REQUIRED = {
    "secret_key": "x" * 32,
    "firebase_project_id": "reference-prod",
    "frontend_base_url": "https://app.example.com",
    "database_url": "postgresql://u:p@localhost:5433/db",
    "redis_url": "redis://localhost:6380/0",
}


def test_meta_exposes_only_public_flags(client: TestClient):
    assert client.get("/api/v1/meta").json() == {
        "api_version": "1",
        "environment": "test",
        "features": {"maintenance_banner": True},
    }


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real environment variables win over arguments. The app's lifespan
    exports FIREBASE_AUTH_EMULATOR_HOST (firebase-admin reads only the process
    environment), so tests that build deployed settings must not inherit it."""
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)


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
        ({"environment": "test", **{**REQUIRED, "secret_key": "short"}}, "at least 32 characters"),
        (
            {
                "environment": "production",
                "firebase_auth_emulator_host": "127.0.0.1:9099",
                **REQUIRED,
            },
            "must not be set",
        ),
        (
            {"environment": "production", **{**REQUIRED, "firebase_project_id": "demo-x"}},
            "emulator-only",
        ),
        (
            {
                "environment": "production",
                **{**REQUIRED, "frontend_base_url": "http://app.example.com"},
            },
            "must use https",
        ),
        (
            {"environment": "production", "argon2_time_cost": 1, **REQUIRED},
            "may not be lowered",
        ),
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
