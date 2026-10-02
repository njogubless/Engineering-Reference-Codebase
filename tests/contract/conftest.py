import os
from pathlib import Path
from typing import Any

import pytest
import yaml

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"

# scripts/contract-check.sh starts both backends on these ports.
BACKENDS = {
    "django": os.environ.get("DJANGO_BASE_URL", "http://localhost:8411"),
    "fastapi": os.environ.get("FASTAPI_BASE_URL", "http://localhost:8421"),
}


@pytest.fixture(scope="session")
def contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text())


@pytest.fixture(params=sorted(BACKENDS))
def base_url(request: pytest.FixtureRequest) -> str:
    return BACKENDS[request.param]
