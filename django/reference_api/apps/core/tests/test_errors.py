"""Every error path produces the same Problem Details shape (contracts/openapi.yaml)."""

import logging
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.core.errors import flatten_validation_errors

pytestmark = pytest.mark.urls("apps.core.tests.urls")

PROBLEM_KEYS = {"type", "title", "status", "code", "request_id"}


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def assert_problem(response, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response["Content-Type"] == "application/problem+json"
    body = response.json()
    assert body.keys() >= PROBLEM_KEYS
    assert body["status"] == status
    assert body["code"] == code
    assert body["request_id"] == response["X-Request-ID"]
    return body


def test_serializer_validation_is_422_with_flat_field_paths(client):
    response = client.post(
        "/t/validate", {"items": [{"name": "ok"}, {"name": "too long"}]}, format="json"
    )
    body = assert_problem(response, 422, "validation_error")
    fields = {(e["field"], e["code"]) for e in body["errors"]}
    assert fields == {("title", "required"), ("items.1.name", "max_length")}


def test_non_field_errors_have_null_field(client):
    response = client.post("/t/validate", {"title": "forbidden", "items": []}, format="json")
    body = assert_problem(response, 422, "validation_error")
    assert body["errors"] == [
        {"field": None, "code": "invalid", "message": "This title is not allowed."}
    ]


def test_malformed_json_is_400_bad_request(client):
    response = client.post("/t/validate", "{not json", content_type="application/json")
    assert_problem(response, 400, "bad_request")


def test_wrong_content_type_is_415(client):
    response = client.post("/t/validate", "name=x", content_type="text/plain")
    assert_problem(response, 415, "unsupported_media_type")


def test_wrong_method_is_405(client):
    assert_problem(client.delete("/t/validate"), 405, "method_not_allowed")


def test_django_validation_error_from_a_service_maps_to_422(client):
    body = assert_problem(client.get("/t/django-validation"), 422, "validation_error")
    assert body["errors"] == [{"field": "email", "code": "invalid", "message": "Already used."}]


def test_django_permission_denied_maps_to_403(client):
    assert_problem(client.get("/t/django-permission"), 403, "authorization_error")


def test_drf_not_found_maps_to_404(client):
    assert_problem(client.get("/t/drf-not-found"), 404, "not_found")


def test_throttled_sets_retry_after_rounded_up(client):
    response = client.get("/t/throttled")  # wait=12.4s
    body = assert_problem(response, 429, "rate_limited")
    assert response["Retry-After"] == "13"
    assert body["retry_after"] == 13


def test_app_conflict_error_keeps_its_message(client):
    body = assert_problem(client.get("/t/conflict"), 409, "conflict")
    assert body["detail"] == "Version 3 is stale."


def test_external_service_error_is_502(client):
    assert_problem(client.get("/t/external"), 502, "external_service_error")


def test_unexpected_exception_is_500_without_internal_details(client, caplog):
    with caplog.at_level(logging.ERROR, logger="apps.core.errors"):
        response = client.get("/t/crash")
    body = assert_problem(response, 500, "internal_error")
    assert "secret-internal-detail" not in response.content.decode()
    assert body["detail"] == "An unexpected error occurred."
    # ...but the details are in the logs, tagged with the same request ID.
    record = next(r for r in caplog.records if r.getMessage() == "unhandled_exception")
    assert record.exc_info is not None
    assert record.request_id == body["request_id"]


def test_unknown_url_returns_problem_json_not_html(client):
    response = client.get("/no/such/path")
    body = assert_problem(response, 404, "not_found")
    assert body["instance"] == "/no/such/path"


def test_views_are_deny_by_default(client):
    response = client.get("/t/default-permission")
    assert_problem(response, 403, "authorization_error")
    assert "secret" not in response.content.decode()


class TestFlattenValidationErrors:
    def test_nested_lists_and_dicts(self):
        errors = flatten_validation_errors(
            {"a": {"b": ["bad"]}, "c": [{}, {"d": ["worse"]}], "non_field_errors": ["x"]}
        )
        assert [(e.field, e.message) for e in errors] == [
            ("a.b", "bad"),
            ("c.1.d", "worse"),
            (None, "x"),
        ]

    def test_empty_detail_produces_no_errors(self):
        assert flatten_validation_errors({}) == []
        assert flatten_validation_errors([]) == []
