import pytest
from rest_framework.test import APIClient

from apps.core.request_context import get_request_id, resolve_request_id


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_generates_a_request_id_when_missing(client):
    response = client.get("/health/live")
    assert len(response["X-Request-ID"]) == 32


def test_echoes_a_valid_incoming_request_id(client):
    response = client.get("/health/live", HTTP_X_REQUEST_ID="client-abc.123")
    assert response["X-Request-ID"] == "client-abc.123"


@pytest.mark.parametrize("bad", ["has space", "new\nline", "x" * 129, "", "ünïcode"])
def test_replaces_unsafe_incoming_ids(bad):
    assert resolve_request_id(bad) != bad


def test_context_is_cleared_after_the_request(client):
    client.get("/health/live", HTTP_X_REQUEST_ID="leak-check")
    assert get_request_id() is None
