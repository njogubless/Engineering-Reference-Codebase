"""End to end through real SMTP into Mailpit (`make up`; a CI service)."""

import json
import urllib.parse
import urllib.request
import uuid

import httpx2

from tests.conftest import signup

MAILPIT_API = "http://localhost:8025/api/v1"


def messages_to(address: str) -> list[dict[str, object]]:
    query = urllib.parse.urlencode({"query": f"to:{address}"})
    with urllib.request.urlopen(f"{MAILPIT_API}/search?{query}", timeout=5) as response:  # noqa: S310
        return json.loads(response.read())["messages"]


async def test_password_reset_email_is_delivered_over_smtp(api: httpx2.AsyncClient):
    address = f"mailpit-{uuid.uuid4().hex[:8]}@example.com"
    await signup(api, address)
    assert (
        await api.post("/api/v1/auth/password-reset", json={"email": address})
    ).status_code == 202
    [message] = messages_to(address)
    assert message["Subject"] == "Reset your password"
