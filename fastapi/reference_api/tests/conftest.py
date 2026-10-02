import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_TEST = PROJECT_DIR / ".env.test"
# Before any app import: settings read FASTAPI_ENV_FILE when the module loads.
os.environ.setdefault("FASTAPI_ENV_FILE", str(ENV_TEST))

import asyncio  # noqa: E402

import httpx2  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from scripts.ensure_database import ensure_database  # noqa: E402

PASSWORD = "correct-horse-battery"
# Children first, so foreign keys are satisfied.
TABLES = ("comments", "posts", "refresh_tokens", "users")


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Create the test database and run the real migrations once per session,
    so tests also prove the migrations produce a working schema."""
    asyncio.run(ensure_database())
    command.upgrade(Config(str(PROJECT_DIR / "alembic.ini")), "head")


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=ENV_TEST)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Synchronous client for tests that do not touch the database."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
async def api(app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    """Async client sharing the test's event loop with the app's engine.

    Isolation by deleting all rows (before and after) rather than a rolled-back
    outer transaction: the app commits for real, exactly as in production.
    DELETE, not TRUNCATE: on near-empty tables TRUNCATE's exclusive locks and
    file operations cost ~0.4 s per test; DELETE costs milliseconds.
    """
    async with app.router.lifespan_context(app):
        await _truncate(app)
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        await _truncate(app)


async def _truncate(app: FastAPI) -> None:
    async with app.state.engine.begin() as connection:
        for table in TABLES:
            await connection.execute(text(f"DELETE FROM {table}"))  # noqa: S608 - constant names


async def signup(api: httpx2.AsyncClient, email: str, display_name: str = "User") -> dict[str, str]:
    """Register + log in through the real endpoints; returns auth headers."""
    response = await api.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": display_name},
    )
    assert response.status_code == 201, response.json()
    tokens = (
        await api.post("/api/v1/auth/token", json={"email": email, "password": PASSWORD})
    ).json()
    return {"Authorization": f"Bearer {tokens['access']}"}
