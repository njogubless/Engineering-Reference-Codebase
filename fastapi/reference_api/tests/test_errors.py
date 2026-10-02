"""Every error path produces the same Problem Details shape as the Django API."""

import logging
from typing import Annotated, Any

import pytest
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.errors import ConflictError, ExternalServiceError, NotFoundError

PROBLEM_KEYS = {"type", "title", "status", "code", "request_id"}


class Item(BaseModel):
    name: str = Field(max_length=5)


class Order(BaseModel):
    title: str
    items: list[Item]


@pytest.fixture
def app(app: FastAPI) -> FastAPI:
    @app.post("/t/validate")
    async def validate(order: Order) -> Order:
        return order

    @app.get("/t/query")
    async def query(limit: Annotated[int, Query(le=100)]) -> dict[str, int]:
        return {"limit": limit}

    @app.get("/t/not-found")
    async def not_found() -> None:
        raise NotFoundError("Post 7 does not exist.")

    @app.get("/t/conflict")
    async def conflict() -> None:
        raise ConflictError("Version 3 is stale.")

    @app.get("/t/external")
    async def external() -> None:
        raise ExternalServiceError("Payment provider unavailable.")

    @app.get("/t/throttled")
    async def throttled() -> None:
        raise HTTPException(status_code=429, headers={"Retry-After": "12"})

    @app.get("/t/crash")
    async def crash() -> None:
        raise KeyError("secret-internal-detail")

    return app


def assert_problem(response, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body.keys() >= PROBLEM_KEYS
    assert body["status"] == status
    assert body["code"] == code
    assert body["request_id"] == response.headers["x-request-id"]
    return body


def test_body_validation_is_422_with_django_compatible_codes(client: TestClient):
    response = client.post("/t/validate", json={"items": [{"name": "ok"}, {"name": "too long"}]})
    body = assert_problem(response, 422, "validation_error")
    fields = {(e["field"], e["code"]) for e in body["errors"]}
    assert fields == {("title", "required"), ("items.1.name", "max_length")}


def test_query_validation_reports_the_parameter_name(client: TestClient):
    body = assert_problem(client.get("/t/query", params={"limit": 500}), 422, "validation_error")
    assert body["errors"][0]["field"] == "limit"
    assert body["errors"][0]["code"] == "max_value"


def test_malformed_json_is_400_not_422(client: TestClient):
    response = client.post(
        "/t/validate", content="{not json", headers={"content-type": "application/json"}
    )
    assert_problem(response, 400, "bad_request")


def test_wrong_content_type_is_415_like_django(client: TestClient):
    response = client.post("/t/validate", content="name=x", headers={"content-type": "text/plain"})
    assert_problem(response, 415, "unsupported_media_type")


def test_wrong_method_is_405(client: TestClient):
    assert_problem(client.delete("/t/validate"), 405, "method_not_allowed")


def test_unknown_route_is_404_problem(client: TestClient):
    body = assert_problem(client.get("/no/such/path"), 404, "not_found")
    assert body["instance"] == "/no/such/path"


def test_app_errors_keep_their_message(client: TestClient):
    assert assert_problem(client.get("/t/not-found"), 404, "not_found")["detail"] == (
        "Post 7 does not exist."
    )
    assert assert_problem(client.get("/t/conflict"), 409, "conflict")["detail"] == (
        "Version 3 is stale."
    )


def test_external_service_error_is_502(client: TestClient):
    assert_problem(client.get("/t/external"), 502, "external_service_error")


def test_rate_limited_has_retry_after(client: TestClient):
    response = client.get("/t/throttled")
    body = assert_problem(response, 429, "rate_limited")
    assert response.headers["retry-after"] == "12"
    assert body["retry_after"] == 12


def test_unexpected_exception_is_500_with_request_id_and_no_internals(
    client: TestClient, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.ERROR, logger="app.request"):
        response = client.get("/t/crash", headers={"X-Request-ID": "crash-1"})
    body = assert_problem(response, 500, "internal_error")
    assert body["request_id"] == "crash-1"
    assert "secret-internal-detail" not in response.text
    record = next(r for r in caplog.records if r.getMessage() == "unhandled_exception")
    assert record.exc_info is not None
    assert getattr(record, "request_id", None) == "crash-1"


def test_error_responses_carry_cors_headers_for_allowed_origins(client: TestClient):
    response = client.get("/t/crash", headers={"Origin": "http://app.test"})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://app.test"
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()
