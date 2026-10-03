"""Typed, env-driven settings (pydantic-settings).

Compare with Django's settings.py: same rules (required values have no
default, safe defaults, cross-setting invariants checked at startup), but the
FastAPI version gets them from a typed model — a typo in a setting or flag
name is a type error, not a runtime surprise.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]

PROJECT_DIR = Path(__file__).resolve().parents[2]

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 64 * 1024


class Settings(BaseSettings):
    # A local .env file is a development convenience; real environment
    # variables always win. FASTAPI_ENV_FILE selects another file (e.g. .env.test).
    model_config = SettingsConfigDict(
        env_file=os.environ.get("FASTAPI_ENV_FILE", PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment
    debug: bool = False
    # Signs access tokens (HMAC-SHA256): at least 32 bytes, in every environment.
    secret_key: str = Field(min_length=32)
    access_token_ttl_seconds: int = Field(default=15 * 60, gt=0)
    # Argon2id cost. Defaults are argon2-cffi's recommendation; tests lower
    # them for speed (like Django's test-only MD5 hasher). Deployed
    # environments may raise but never lower them (validated below).
    argon2_time_cost: int = Field(default=ARGON2_TIME_COST, ge=1)
    argon2_memory_cost_kib: int = Field(default=ARGON2_MEMORY_COST_KIB, ge=8)
    refresh_token_ttl_days: int = Field(default=7, gt=0)
    database_url: PostgresDsn
    redis_url: RedisDsn
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Feature flags: attributes, so `settings.feature_serach_v2` fails type checking.
    feature_search_v2: bool = False
    feature_maintenance_banner: bool = False

    readiness_timeout_seconds: float = Field(default=2.0, gt=0)

    # Firebase: verifying ID tokens needs only the project id. The emulator
    # host makes firebase-admin accept unsigned emulator tokens.
    firebase_project_id: str
    firebase_auth_emulator_host: str = ""

    # Email (Mailpit in development) and where links in emails point.
    email_host: str = "localhost"
    email_port: int = 1025
    email_username: str = ""
    email_password: str = ""
    email_use_tls: bool = False
    default_from_email: str = "Reference <no-reply@reference.test>"
    frontend_base_url: str
    password_reset_ttl_seconds: int = Field(default=60 * 60, gt=0)
    email_verification_ttl_seconds: int = Field(default=3 * 24 * 60 * 60, gt=0)

    # Browser origins allowed to call the API (comma-separated, same format as Django).
    cors_allowed_origins: Annotated[list[str], NoDecode] = []

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def deployed_environments_are_safe(self) -> Self:
        if self.environment in ("staging", "production"):
            if self.debug:
                raise ValueError("DEBUG must be off in staging/production.")
            if (
                self.argon2_time_cost < ARGON2_TIME_COST
                or self.argon2_memory_cost_kib < ARGON2_MEMORY_COST_KIB
            ):
                raise ValueError("Argon2 cost may not be lowered in staging/production.")
            if self.firebase_auth_emulator_host:
                raise ValueError(
                    "FIREBASE_AUTH_EMULATOR_HOST must not be set in staging/production."
                )
            if self.firebase_project_id.startswith("demo-"):
                raise ValueError("FIREBASE_PROJECT_ID is an emulator-only demo project.")
            if not self.frontend_base_url.startswith("https://"):
                raise ValueError("FRONTEND_BASE_URL must use https in staging/production.")
            if "*" in self.cors_allowed_origins:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must list explicit origins in staging/production."
                )
        return self

    @property
    def public_features(self) -> dict[str, bool]:
        """Flags safe to expose to clients (GET /api/v1/meta)."""
        return {"maintenance_banner": self.feature_maintenance_banner}

    @property
    def async_database_url(self) -> str:
        # SQLAlchemy selects the async driver from the URL scheme.
        _scheme, rest = str(self.database_url).split("://", 1)
        return f"postgresql+asyncpg://{rest}"


@lru_cache
def get_settings() -> Settings:
    """Read the environment once. Tests clear the cache or override the dependency."""
    return Settings()  # required values come from the environment
