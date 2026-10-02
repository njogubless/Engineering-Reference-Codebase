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
    response = httpx.request(method, base_url + path, headers={"X-Request-ID": "contract-1"}, timeout=10)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    problem_validator.validate(body)
    assert body["code"] == code
    assert body["request_id"] == "contract-1"
    assert response.headers["x-request-id"] == "contract-1"
