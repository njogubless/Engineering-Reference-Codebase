import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def test_preflight_allows_configured_origin(client):
    response = client.options(
        "/api/v1/meta",
        HTTP_ORIGIN="http://app.test",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-request-id",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "http://app.test"


def test_unlisted_origin_gets_no_cors_headers(client):
    response = client.get("/api/v1/meta", HTTP_ORIGIN="http://evil.test")
    assert "Access-Control-Allow-Origin" not in response


def test_request_id_is_readable_by_browser_javascript(client):
    response = client.get("/api/v1/meta", HTTP_ORIGIN="http://app.test")
    assert "x-request-id" in response["Access-Control-Expose-Headers"]


def test_error_responses_carry_cors_headers(client):
    response = client.get("/no/such/path", HTTP_ORIGIN="http://app.test")
    assert response.status_code == 404
    assert response["Access-Control-Allow-Origin"] == "http://app.test"
