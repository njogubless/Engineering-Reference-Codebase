import pytest
from rest_framework.test import APIClient

from apps.core import views


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_liveness_never_touches_dependencies(client, monkeypatch):
    def explode() -> None:
        raise AssertionError("liveness must not check dependencies")

    monkeypatch.setitem(views.READINESS_CHECKS, "database", explode)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_ok_against_real_postgres_and_redis(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_readiness_503_when_a_dependency_fails_without_leaking_details(client, monkeypatch):
    def down() -> None:
        raise ConnectionError("redis://:supersecret@10.0.0.5 refused")

    monkeypatch.setitem(views.READINESS_CHECKS, "database", lambda: None)
    monkeypatch.setitem(views.READINESS_CHECKS, "redis", down)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "ok", "redis": "fail"},
    }
    assert "supersecret" not in response.content.decode()


def test_health_endpoints_need_no_credentials(client):
    assert client.get("/health/live").status_code == 200
