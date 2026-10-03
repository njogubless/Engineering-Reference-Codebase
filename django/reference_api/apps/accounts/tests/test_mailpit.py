"""End to end through real SMTP: the configured backend delivers to Mailpit
(`make up`; a CI service). Unit tests use Django's in-memory outbox instead."""

import json
import urllib.parse
import urllib.request
import uuid

import pytest
from django.test import override_settings

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(client, run_commit_hooks):
    return run_commit_hooks(client)


MAILPIT_API = "http://localhost:8025/api/v1"


def messages_to(address: str) -> list[dict[str, object]]:
    query = urllib.parse.urlencode({"query": f"to:{address}"})
    with urllib.request.urlopen(f"{MAILPIT_API}/search?{query}", timeout=5) as response:  # noqa: S310
        return json.loads(response.read())["messages"]


@override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
def test_password_reset_email_is_delivered_over_smtp(client, make_user):
    address = f"mailpit-{uuid.uuid4().hex[:8]}@example.com"
    make_user(address)
    assert (
        client.post("/api/v1/auth/password-reset", {"email": address}, format="json").status_code
        == 202
    )
    [message] = messages_to(address)
    assert message["Subject"] == "Reset your password"
