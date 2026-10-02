from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

ENV_TEST = Path(__file__).resolve().parents[1] / ".env.test"


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=ENV_TEST)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # The context manager runs the lifespan (engine + Redis client), and
    # raise_server_exceptions=False lets us observe 500 responses.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
