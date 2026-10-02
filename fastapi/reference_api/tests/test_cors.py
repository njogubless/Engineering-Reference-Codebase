from fastapi.testclient import TestClient


def test_preflight_allows_configured_origin(client: TestClient):
    response = client.options(
        "/api/v1/meta",
        headers={
            "Origin": "http://app.test",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-request-id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://app.test"


def test_unlisted_origin_gets_no_cors_headers(client: TestClient):
    response = client.get("/api/v1/meta", headers={"Origin": "http://evil.test"})
    assert "access-control-allow-origin" not in response.headers


def test_request_id_is_readable_by_browser_javascript(client: TestClient):
    response = client.get("/api/v1/meta", headers={"Origin": "http://app.test"})
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()
