"""Property-based conformance: Schemathesis generates requests from the
contract and validates every response (status, content type, body schema)
against it, for each backend."""

import schemathesis

from conftest import BACKENDS, CONTRACT_PATH

schema = schemathesis.openapi.from_path(CONTRACT_PATH)


@schema.parametrize()
def test_django_conforms(case: schemathesis.Case) -> None:
    case.call_and_validate(base_url=BACKENDS["django"])


@schema.parametrize()
def test_fastapi_conforms(case: schemathesis.Case) -> None:
    case.call_and_validate(base_url=BACKENDS["fastapi"])
