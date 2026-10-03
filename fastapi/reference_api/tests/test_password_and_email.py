import re
from urllib.parse import unquote

import httpx2
import pytest

from app.core.email import OutboxEmailSender
from tests.conftest import PASSWORD, signup

TOKEN = "/api/v1/auth/token"
REFRESH = "/api/v1/auth/token/refresh"
RESET = "/api/v1/auth/password-reset"
CONFIRM = "/api/v1/auth/password-reset/confirm"
NEW_PASSWORD = "brand-new-password-42"


def link_token(outbox: OutboxEmailSender) -> str:
    match = re.search(r"token=([^\s&]+)", outbox.messages[-1].body)
    assert match is not None
    return unquote(match.group(1))


async def login(api: httpx2.AsyncClient, password: str = PASSWORD) -> httpx2.Response:
    return await api.post(TOKEN, json={"email": "ada@example.com", "password": password})


@pytest.fixture
async def ada(api: httpx2.AsyncClient) -> dict[str, str]:
    return await signup(api, "ada@example.com", "Ada")


class TestPasswordReset:
    async def test_same_answer_for_known_and_unknown_emails(self, api, ada, outbox):
        for email in ("ada@example.com", "nobody@example.com"):
            assert (await api.post(RESET, json={"email": email})).status_code == 202
        assert [m.to for m in outbox.messages] == ["ada@example.com"]
        assert "http://app.test/reset-password?token=" in outbox.messages[0].body

    async def test_reset_changes_password_and_signs_out_everywhere(self, api, ada, outbox):
        old_refresh = (await login(api)).json()["refresh"]
        await api.post(RESET, json={"email": "ada@example.com"})
        response = await api.post(
            CONFIRM, json={"token": link_token(outbox), "password": NEW_PASSWORD}
        )
        assert response.status_code == 204
        assert (await login(api)).status_code == 401
        assert (await login(api, NEW_PASSWORD)).status_code == 200
        assert (await api.post(REFRESH, json={"refresh": old_refresh})).status_code == 401

    async def test_a_reset_link_works_only_once(self, api, ada, outbox):
        await api.post(RESET, json={"email": "ada@example.com"})
        token = link_token(outbox)
        await api.post(CONFIRM, json={"token": token, "password": NEW_PASSWORD})
        again = await api.post(CONFIRM, json={"token": token, "password": "another-password-77"})
        assert again.status_code == 422
        assert again.json()["errors"][0]["field"] == "token"

    async def test_a_verification_token_cannot_reset_a_password(self, api, ada, outbox):
        """Tokens are bound to a purpose."""
        await api.post("/api/v1/auth/email-verification", headers=ada)
        response = await api.post(
            CONFIRM, json={"token": link_token(outbox), "password": NEW_PASSWORD}
        )
        assert response.status_code == 422

    async def test_garbage_tokens_are_field_errors(self, api, ada):
        response = await api.post(CONFIRM, json={"token": "garbage", "password": NEW_PASSWORD})
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "token"


class TestChangePassword:
    async def test_requires_the_current_password(self, api, ada):
        response = await api.post(
            "/api/v1/auth/password",
            json={"current_password": "wrong", "new_password": NEW_PASSWORD},
            headers=ada,
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "incorrect"

    async def test_revokes_other_sessions_and_returns_new_tokens(self, api, ada):
        other_session = (await login(api)).json()["refresh"]
        response = await api.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            headers=ada,
        )
        assert response.status_code == 200
        assert (await api.post(REFRESH, json={"refresh": other_session})).status_code == 401
        assert (
            await api.post(REFRESH, json={"refresh": response.json()["refresh"]})
        ).status_code == 200

    async def test_weak_new_password_is_reported_on_new_password(self, api, ada):
        response = await api.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "1234567890"},
            headers=ada,
        )
        assert response.status_code == 422
        assert {e["field"] for e in response.json()["errors"]} == {"new_password"}


class TestEmailVerification:
    async def test_request_and_confirm_once(self, api, ada, outbox):
        assert (await api.post("/api/v1/auth/email-verification", headers=ada)).status_code == 202
        token = link_token(outbox)
        confirm = "/api/v1/auth/email-verification/confirm"
        assert (await api.post(confirm, json={"token": token})).status_code == 204
        assert (await api.get("/api/v1/auth/me", headers=ada)).json()["email_verified"] is True
        assert (await api.post(confirm, json={"token": token})).status_code == 422

    async def test_already_verified_users_get_no_email(self, api, ada, outbox):
        await api.post("/api/v1/auth/email-verification", headers=ada)
        await api.post(
            "/api/v1/auth/email-verification/confirm", json={"token": link_token(outbox)}
        )
        await api.post("/api/v1/auth/email-verification", headers=ada)
        assert len(outbox.messages) == 1

    async def test_requires_authentication(self, api):
        assert (await api.post("/api/v1/auth/email-verification")).status_code == 401
