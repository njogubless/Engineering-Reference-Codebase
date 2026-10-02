import logging

import pytest
from fastapi.testclient import TestClient

from app.core.request_context import get_request_id, resolve_request_id


def test_generates_a_request_id_when_missing(client: TestClient):
    assert len(client.get("/health/live").headers["x-request-id"]) == 32


def test_echoes_a_valid_incoming_request_id(client: TestClient):
    response = client.get("/health/live", headers={"X-Request-ID": "client-abc.123"})
    assert response.headers["x-request-id"] == "client-abc.123"


@pytest.mark.parametrize("bad", ["has space", "x" * 129, "", "ünïcode"])
def test_replaces_unsafe_incoming_ids(bad: str):
    assert resolve_request_id(bad) != bad


def test_context_is_cleared_after_the_request(client: TestClient):
    client.get("/health/live", headers={"X-Request-ID": "leak-check"})
    assert get_request_id() is None


def test_logs_one_completion_line_per_request(client: TestClient, caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/health/live?token=should-not-be-logged", headers={"X-Request-ID": "r-1"})
    [record] = [r for r in caplog.records if r.getMessage() == "request_completed"]
    assert getattr(record, "request_id", None) == "r-1"
    assert getattr(record, "status", None) == 200
    assert getattr(record, "path", None) == "/health/live"  # query strings may carry secrets
