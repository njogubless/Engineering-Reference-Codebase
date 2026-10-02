import os
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"

# scripts/contract-check.sh starts both backends on these ports.
BACKENDS = {
    "django": os.environ.get("DJANGO_BASE_URL", "http://localhost:8411"),
    "fastapi": os.environ.get("FASTAPI_BASE_URL", "http://localhost:8421"),
}

PASSWORD = "contract-test-password"  # noqa: S105 - throwaway account in a throwaway database


def auth_headers(base_url: str) -> dict[str, str]:
    """Register a fresh user through the contract's own endpoints and log in."""
    email = f"contract-{uuid.uuid4().hex[:12]}@example.com"
    registered = httpx.post(
        f"{base_url}/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Contract"},
        timeout=10,
    )
    registered.raise_for_status()
    tokens = httpx.post(
        f"{base_url}/api/v1/auth/token", json={"email": email, "password": PASSWORD}, timeout=10
    )
    tokens.raise_for_status()
    return {"Authorization": f"Bearer {tokens.json()['access']}"}


@pytest.fixture(scope="session")
def contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text())


@pytest.fixture(params=sorted(BACKENDS))
def base_url(request: pytest.FixtureRequest) -> str:
    return BACKENDS[request.param]
