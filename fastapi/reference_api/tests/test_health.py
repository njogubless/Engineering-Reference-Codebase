import asyncio

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.health import router as health


def test_liveness_never_touches_dependencies(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def explode(request: Request) -> None:
        raise AssertionError("liveness must not check dependencies")

    monkeypatch.setitem(health.READINESS_CHECKS, "database", explode)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_ok_against_real_postgres_and_redis(client: TestClient):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_readiness_503_without_leaking_details(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def down(request: Request) -> None:
        raise ConnectionError("redis://:supersecret@10.0.0.5 refused")

    monkeypatch.setitem(health.READINESS_CHECKS, "redis", down)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "ok", "redis": "fail"},
    }
    assert "supersecret" not in response.text


def test_a_hanging_dependency_times_out_instead_of_hanging_the_probe(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, settings
):
    settings.readiness_timeout_seconds = 0.05

    async def hang(request: Request) -> None:
        await asyncio.sleep(10)

    monkeypatch.setitem(health.READINESS_CHECKS, "database", hang)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "fail"
