"""Property-based conformance: Schemathesis generates requests from the
contract and validates every response (status, content type, headers, body
schema) against it, for each backend — authenticated, so protected
operations are exercised beyond their 401."""

import os

import pytest
import schemathesis
from schemathesis.config import SchemathesisConfig

from conftest import BACKENDS, CONTRACT_PATH, auth_headers

config = SchemathesisConfig.discover()  # tests/contract/schemathesis.toml
if os.environ.get("CONTRACT_FUZZ"):
    # `make fuzz-contract`: fresh random inputs and many more of them.
    config.projects.default.generation.deterministic = False
    config.projects.default.generation.max_examples = 500

schema = schemathesis.openapi.from_path(CONTRACT_PATH, config=config)


@pytest.fixture(scope="module")
def django_auth() -> dict[str, str]:
    return auth_headers(BACKENDS["django"])


@pytest.fixture(scope="module")
def fastapi_auth() -> dict[str, str]:
    return auth_headers(BACKENDS["fastapi"])


@schema.parametrize()
def test_django_conforms(case: schemathesis.Case, django_auth: dict[str, str]) -> None:
    case.call_and_validate(base_url=BACKENDS["django"], headers=django_auth)


@schema.parametrize()
def test_fastapi_conforms(case: schemathesis.Case, fastapi_auth: dict[str, str]) -> None:
    case.call_and_validate(base_url=BACKENDS["fastapi"], headers=fastapi_auth)
