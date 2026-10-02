"""Both backends produce byte-for-byte compatible error shapes.

The contract's operations cover the happy paths; these requests force the
error paths every client has to handle and validate them against the
contract's `Problem` schema.
"""

from typing import Any

import httpx
import jsonschema_rs
import pytest


@pytest.fixture(scope="module")
def problem_validator(contract: dict[str, Any]) -> jsonschema_rs.Draft202012Validator:
    # Resolve $refs against the whole contract document.
    schema = {"$ref": "#/components/schemas/Problem", "components": contract["components"]}
    return jsonschema_rs.Draft202012Validator(schema)


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [
        ("GET", "/api/v1/does-not-exist", 404, "not_found"),
        ("DELETE", "/api/v1/meta", 405, "method_not_allowed"),
        ("GET", "/api/v1/auth/me", 401, "authentication_error"),
        ("GET", "/api/v1/posts/00000000-0000-7000-8000-000000000000", 404, "not_found"),
        ("GET", "/api/v1/posts?limit=500", 422, "validation_error"),
        ("POST", "/api/v1/auth/token", 401, "authentication_error"),
    ],
)
def test_errors_are_problem_details(
    base_url: str,
    problem_validator: jsonschema_rs.Draft202012Validator,
    method: str,
    path: str,
    status: int,
    code: str,
):
    body_for = {"POST": {"email": "nobody@example.com", "password": "wrong-password"}}
    response = httpx.request(
        method,
        base_url + path,
        headers={"X-Request-ID": "contract-1"},
        json=body_for.get(method),
        timeout=10,
    )
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    problem_validator.validate(body)
    assert body["code"] == code
    assert body["request_id"] == "contract-1"
    assert response.headers["x-request-id"] == "contract-1"


def test_both_backends_report_identical_field_errors() -> None:
    """Same invalid input -> same codes and field paths from both backends."""
    from conftest import BACKENDS

    payload = {"email": "not-an-email", "password": "short", "display_name": "", "role": "admin"}
    results = {}
    for name, url in BACKENDS.items():
        response = httpx.post(f"{url}/api/v1/auth/register", json=payload, timeout=10)
        assert response.status_code == 422
        results[name] = sorted((e["field"], e["code"]) for e in response.json()["errors"])
    assert {field for field, _ in results["django"]} == {field for field, _ in results["fastapi"]}
    assert ("role", "unknown_field") in results["django"]
    assert ("role", "unknown_field") in results["fastapi"]
