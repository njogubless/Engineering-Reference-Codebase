from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from conftest import PASSWORD

pytestmark = pytest.mark.django_db

REGISTER = "/api/v1/auth/register"
TOKEN = "/api/v1/auth/token"
REFRESH = "/api/v1/auth/token/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def obtain(
    client: APIClient, email: str = "ada@example.com", password: str = PASSWORD
) -> dict[str, Any]:
    response = client.post(TOKEN, {"email": email, "password": password}, format="json")
    assert response.status_code == 200, response.json()
    return response.json()


class TestRegister:
    def test_creates_user_with_normalized_email_and_hashed_password(self, client):
        response = client.post(
            REGISTER,
            {"email": " Ada@Example.COM ", "password": PASSWORD, "display_name": "Ada"},
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "ada@example.com"
        assert set(body) == {
            "id",
            "email",
            "email_verified",
            "display_name",
            "date_joined",
        }  # never the password
        user = User.objects.get()
        assert user.password != PASSWORD and user.check_password(PASSWORD)

    def test_duplicate_email_is_a_field_error_regardless_of_case(self, client, user):
        response = client.post(
            REGISTER,
            {"email": "ADA@example.com", "password": PASSWORD, "display_name": "Imposter"},
            format="json",
        )
        assert response.status_code == 422
        assert response.json()["errors"] == [
            {
                "field": "email",
                "code": "unique",
                "message": "An account with this email already exists.",
            }
        ]

    @pytest.mark.parametrize("password", ["short", "1234567890123", "password123"])
    def test_weak_passwords_are_rejected_on_the_password_field(self, client, password):
        response = client.post(
            REGISTER,
            {"email": "x@example.com", "password": password, "display_name": "X"},
            format="json",
        )
        assert response.status_code == 422
        assert {e["field"] for e in response.json()["errors"]} == {"password"}

    def test_unknown_fields_are_rejected(self, client):
        response = client.post(
            REGISTER,
            {"email": "x@example.com", "password": PASSWORD, "display_name": "X", "is_staff": True},
            format="json",
        )
        assert response.status_code == 422
        assert response.json()["errors"][0] == {
            "field": "is_staff",
            "code": "unknown_field",
            "message": "Unknown field.",
        }


class TestTokens:
    def test_login_is_case_insensitive_and_returns_a_pair(self, client, user):
        tokens = obtain(client, "ADA@example.com")
        assert set(tokens) == {"access", "refresh"}

    @pytest.mark.parametrize(
        ("email", "password"),
        [("ada@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)],
    )
    def test_wrong_email_and_wrong_password_are_indistinguishable(
        self, client, user, email, password
    ):
        response = client.post(TOKEN, {"email": email, "password": password}, format="json")
        assert response.status_code == 401
        assert response.json()["code"] == "authentication_error"
        assert response.json()["detail"] == "No active account found with the given credentials"

    def test_access_token_authenticates_requests(self, client, user):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {obtain(client)['access']}")
        assert client.get(ME).json()["email"] == "ada@example.com"

    def test_missing_credentials_are_401_with_a_bearer_challenge(self, client):
        response = client.get(ME)
        assert response.status_code == 401
        assert response["WWW-Authenticate"].startswith("Bearer")
        assert response.json()["code"] == "authentication_error"

    def test_invalid_token_is_401_with_a_readable_detail(self, client):
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-jwt")
        response = client.get(ME)
        assert response.status_code == 401
        assert response.json()["detail"] == "Given token not valid for any token type"

    def test_refresh_rotates_and_the_old_refresh_token_stops_working(self, client, user):
        first = obtain(client)
        rotated = client.post(REFRESH, {"refresh": first["refresh"]}, format="json")
        assert rotated.status_code == 200
        assert rotated.json()["refresh"] != first["refresh"]

        reused = client.post(REFRESH, {"refresh": first["refresh"]}, format="json")
        assert reused.status_code == 401

    def test_logout_revokes_the_refresh_token_and_is_idempotent(self, client, user):
        tokens = obtain(client)
        assert client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json").status_code == 204
        assert client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json").status_code == 204
        assert (
            client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json").status_code == 401
        )

    def test_logout_with_garbage_is_still_204(self, client):
        assert client.post(LOGOUT, {"refresh": "garbage"}, format="json").status_code == 204

    def test_inactive_users_cannot_log_in(self, client, user):
        user.is_active = False
        user.save()
        response = client.post(TOKEN, {"email": user.email, "password": PASSWORD}, format="json")
        assert response.status_code == 401


def test_login_lookup_uses_the_email_index(user):
    """EXPLAIN proves the login query can use an index (no sequential scan)."""
    from django.db import connection

    queryset = User.objects.filter(email="ada@example.com")
    with connection.cursor() as cursor:
        cursor.execute(
            "SET enable_seqscan = off"
        )  # tiny tables: force the planner to show its options
        plan = queryset.explain()
    assert "Index" in plan and "Seq Scan" not in plan


def test_wrong_json_type_is_rejected_not_coerced(client):
    """Found by Schemathesis: DRF turned {"refresh": 0} into "0"."""
    response = client.post(LOGOUT, {"refresh": 0}, format="json")
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "refresh", "code": "invalid", "message": "Not a valid string."}
    ]


@pytest.mark.parametrize(
    ("value", "code"),
    [("a\x00b", "null_characters_not_allowed"), ("a\ud800b", "surrogate_characters_not_allowed")],
)
def test_unstorable_characters_are_422(client, value, code):
    import json

    response = client.post(
        REGISTER,
        json.dumps({"email": "x@example.com", "password": PASSWORD, "display_name": value}),
        content_type="application/json",
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == code


def test_passwords_are_not_trimmed_at_login(client):
    """Found by Schemathesis: registration kept surrounding spaces, login trimmed them."""
    password = "  spaced-out-password  "
    client.post(
        REGISTER,
        {"email": "s@example.com", "password": password, "display_name": "S"},
        format="json",
    )
    response = client.post(TOKEN, {"email": "s@example.com", "password": password}, format="json")
    assert response.status_code == 200


@pytest.mark.parametrize("email", ["a@x.test", "a@printer.local", "a@localhost"])
def test_special_use_email_domains_are_rejected_like_fastapi(client, email):
    """Found by Schemathesis: Django accepted these, FastAPI (EmailStr) did not."""
    response = client.post(
        REGISTER, {"email": email, "password": PASSWORD, "display_name": "X"}, format="json"
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "email"
