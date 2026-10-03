import re

import pytest
from django.core import mail

from conftest import PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(client, run_commit_hooks):
    return run_commit_hooks(client)


@pytest.fixture
def client_as(client_as, run_commit_hooks):
    return lambda user: run_commit_hooks(client_as(user))


RESET = "/api/v1/auth/password-reset"
CONFIRM = "/api/v1/auth/password-reset/confirm"
TOKEN = "/api/v1/auth/token"
REFRESH = "/api/v1/auth/token/refresh"
NEW_PASSWORD = "brand-new-password-42"


def token_from_last_email() -> str:
    match = re.search(r"token=([^\s&]+)", str(mail.outbox[-1].body))
    assert match is not None
    from urllib.parse import unquote

    return unquote(match.group(1))


def login(client, password=PASSWORD):
    return client.post(TOKEN, {"email": "ada@example.com", "password": password}, format="json")


class TestPasswordReset:
    def test_unknown_and_known_emails_get_the_same_answer(self, client, user):
        for email in ("ada@example.com", "nobody@example.com"):
            assert client.post(RESET, {"email": email}, format="json").status_code == 202
        assert len(mail.outbox) == 1  # only the real account got an email
        assert mail.outbox[0].to == ["ada@example.com"]
        assert "http://app.test/reset-password?token=" in mail.outbox[0].body

    def test_reset_changes_the_password_and_signs_out_everywhere(self, client, user):
        old_refresh = login(client).json()["refresh"]
        client.post(RESET, {"email": "ada@example.com"}, format="json")
        token = token_from_last_email()

        assert (
            client.post(
                CONFIRM, {"token": token, "password": NEW_PASSWORD}, format="json"
            ).status_code
            == 204
        )
        assert login(client).status_code == 401
        assert login(client, NEW_PASSWORD).status_code == 200
        assert client.post(REFRESH, {"refresh": old_refresh}, format="json").status_code == 401

    def test_a_reset_link_works_only_once(self, client, user):
        client.post(RESET, {"email": "ada@example.com"}, format="json")
        token = token_from_last_email()
        client.post(CONFIRM, {"token": token, "password": NEW_PASSWORD}, format="json")
        again = client.post(
            CONFIRM, {"token": token, "password": "another-password-77"}, format="json"
        )
        assert again.status_code == 422
        assert again.json()["errors"][0]["field"] == "token"

    @pytest.mark.parametrize("token", ["garbage", "MQ.abc", ""])
    def test_bad_tokens_are_field_errors(self, client, user, token):
        response = client.post(CONFIRM, {"token": token, "password": NEW_PASSWORD}, format="json")
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "token"

    def test_weak_new_password_is_rejected(self, client, user):
        client.post(RESET, {"email": "ada@example.com"}, format="json")
        response = client.post(
            CONFIRM, {"token": token_from_last_email(), "password": "1234567890"}, format="json"
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "password"


class TestChangePassword:
    def test_requires_the_current_password(self, client_as, user):
        response = client_as(user).post(
            "/api/v1/auth/password",
            {"current_password": "wrong", "new_password": NEW_PASSWORD},
            format="json",
        )
        assert response.status_code == 422
        assert response.json()["errors"][0] == {
            "field": "current_password",
            "code": "incorrect",
            "message": "The current password is incorrect.",
        }

    def test_changes_password_revokes_other_sessions_and_returns_new_tokens(
        self, client, client_as, user
    ):
        other_session = login(client).json()["refresh"]
        response = client_as(user).post(
            "/api/v1/auth/password",
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert set(response.json()) == {"access", "refresh"}
        assert client.post(REFRESH, {"refresh": other_session}, format="json").status_code == 401
        assert (
            client.post(REFRESH, {"refresh": response.json()["refresh"]}, format="json").status_code
            == 200
        )


class TestEmailVerification:
    def test_request_and_confirm(self, client, client_as, user):
        assert client_as(user).post("/api/v1/auth/email-verification").status_code == 202
        assert "http://app.test/verify-email?token=" in mail.outbox[-1].body
        token = token_from_last_email()
        confirm = "/api/v1/auth/email-verification/confirm"
        assert client.post(confirm, {"token": token}, format="json").status_code == 204
        user.refresh_from_db()
        assert user.email_verified is True
        # Single use: verifying changed the hashed state.
        assert client.post(confirm, {"token": token}, format="json").status_code == 422

    def test_already_verified_users_get_no_email(self, client_as, user):
        user.email_verified = True
        user.save()
        assert client_as(user).post("/api/v1/auth/email-verification").status_code == 202
        assert mail.outbox == []

    def test_changing_the_email_invalidates_the_link(self, client, client_as, user):
        client_as(user).post("/api/v1/auth/email-verification")
        token = token_from_last_email()
        user.email = "new@example.com"
        user.save()
        response = client.post(
            "/api/v1/auth/email-verification/confirm", {"token": token}, format="json"
        )
        assert response.status_code == 422

    def test_requires_authentication(self, client):
        assert client.post("/api/v1/auth/email-verification").status_code == 401
