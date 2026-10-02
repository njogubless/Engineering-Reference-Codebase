"""Each backend exposes exactly the operations the contract defines — no more, no fewer.

Catches drift in both directions: an endpoint added to one backend but not the
contract, or a contract operation one backend forgot to implement.
"""

from typing import Any

import httpx
import pytest

from conftest import BACKENDS

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}

# Where each framework serves its generated OpenAPI document.
GENERATED_SCHEMA = {
    "django": "/api/schema?format=json",
    "fastapi": "/openapi.json",
}


def operations(spec: dict[str, Any]) -> set[tuple[str, str, str | None]]:
    return {
        (path, method.upper(), operation.get("operationId"))
        for path, item in spec["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    }


@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_backend_implements_exactly_the_contract_operations(backend: str, contract: dict[str, Any]):
    response = httpx.get(BACKENDS[backend] + GENERATED_SCHEMA[backend], timeout=10)
    response.raise_for_status()
    assert operations(response.json()) == operations(contract)
