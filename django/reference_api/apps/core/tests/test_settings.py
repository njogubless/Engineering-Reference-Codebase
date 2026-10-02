"""Configuration fails fast: bad settings stop the process at startup."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[3]

BASE_ENV = {
    "PATH": os.environ["PATH"],
    "DJANGO_ENV_FILE": "/nonexistent",  # only the variables below
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "DATABASE_URL": "postgres://u:p@localhost:5433/db",
    "REDIS_URL": "redis://localhost:6380/0",
    "SECRET_KEY": "x" * 60,
    "ENVIRONMENT": "production",
}


def load_settings(**overrides: str | None) -> subprocess.CompletedProcess[str]:
    merged = {**BASE_ENV, **overrides}
    env = {key: value for key, value in merged.items() if value is not None}
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=PROJECT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_production_settings_load():
    assert load_settings().returncode == 0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"SECRET_KEY": None}, "SECRET_KEY"),
        ({"DATABASE_URL": None}, "DATABASE_URL"),
        ({"ENVIRONMENT": "prod"}, "ENVIRONMENT must be one of"),
        ({"DEBUG": "true"}, "DEBUG must be off"),
        ({"SECRET_KEY": "short"}, "SECRET_KEY is too weak"),
    ],
)
def test_invalid_settings_fail_at_startup(overrides, message):
    result = load_settings(**overrides)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert message in result.stderr
