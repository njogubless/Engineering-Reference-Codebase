import asyncio
import json

import httpx2
import pytest

from tests.conftest import PASSWORD, signup

REGISTER = "/api/v1/auth/register"
TOKEN = "/api/v1/auth/token"
REFRESH = "/api/v1/auth/token/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


async def login(api: httpx2.AsyncClient, email: str = "ada@example.com") -> dict[str, str]:
    response = await api.post(TOKEN, json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.json()
    return response.json()


@pytest.fixture
async def ada(api: httpx2.AsyncClient) -> dict[str, str]:
    return await signup(api, "ada@example.com", "Ada")


class TestRegister:
    async def test_normalises_email_and_never_returns_the_password(self, api):
        response = await api.post(
            REGISTER,
            json={"email": " Ada@Example.COM ", "password": PASSWORD, "display_name": "Ada"},
        )
        assert response.status_code == 201
        assert response.json()["email"] == "ada@example.com"
        assert set(response.json()) == {"id", "email", "display_name", "date_joined"}

    async def test_duplicate_email_any_case_is_a_field_error(self, api, ada):
        response = await api.post(
            REGISTER, json={"email": "ADA@example.com", "password": PASSWORD, "display_name": "X"}
        )
        assert response.status_code == 422
        assert response.json()["errors"] == [
            {
                "field": "email",
                "code": "unique",
                "message": "An account with this email already exists.",
            }
        ]

    @pytest.mark.parametrize(
        ("password", "code"),
        [
            ("short", "min_length"),
            ("12345678901234", "password_entirely_numeric"),
            ("password1234", "password_too_common"),
            ("ada@example.com", "password_too_similar"),
        ],
    )
    async def test_weak_passwords(self, api, password, code):
        response = await api.post(
            REGISTER, json={"email": "ada@example.com", "password": password, "display_name": "Ada"}
        )
        assert response.status_code == 422
        assert code in {e["code"] for e in response.json()["errors"]}

    async def test_similarity_is_a_ratio_not_a_substring(self, api):
        response = await api.post(
            REGISTER,
            json={
                "email": "c@example.com",
                "password": "contract-test-password",
                "display_name": "Contract",
            },
        )
        assert response.status_code == 201

    async def test_unknown_fields_are_rejected(self, api):
        response = await api.post(
            REGISTER,
            json={
                "email": "x@example.com",
                "password": PASSWORD,
                "display_name": "X",
                "is_staff": True,
            },
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "is_staff"
        assert response.json()["errors"][0]["code"] == "unknown_field"


class TestTokens:
    async def test_login_is_case_insensitive(self, api, ada):
        assert set(await login(api, "ADA@example.com")) == {"access", "refresh"}

    @pytest.mark.parametrize(
        ("email", "password"),
        [("ada@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)],
    )
    async def test_wrong_email_and_wrong_password_are_indistinguishable(
        self, api, ada, email, password
    ):
        response = await api.post(TOKEN, json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json()["detail"] == "No active account found with the given credentials"

    async def test_access_token_authenticates(self, api, ada):
        assert (await api.get(ME, headers=ada)).json()["email"] == "ada@example.com"

    async def test_missing_credentials_are_401_with_bearer_challenge(self, api):
        response = await api.get(ME)
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Bearer")

    async def test_invalid_token_is_401_even_on_public_endpoints(self, api):
        response = await api.get("/api/v1/posts", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    async def test_refresh_rotates_and_old_token_stops_working(self, api, ada):
        first = await login(api)
        rotated = await api.post(REFRESH, json={"refresh": first["refresh"]})
        assert rotated.status_code == 200
        assert rotated.json()["refresh"] != first["refresh"]
        assert (await api.post(REFRESH, json={"refresh": first["refresh"]})).status_code == 401

    async def test_reusing_a_rotated_token_revokes_the_whole_family(self, api, ada):
        """Theft detection: the legitimate client's *current* token dies too."""
        stolen = (await login(api))["refresh"]
        current = (await api.post(REFRESH, json={"refresh": stolen})).json()["refresh"]
        assert (await api.post(REFRESH, json={"refresh": stolen})).status_code == 401  # replay
        assert (await api.post(REFRESH, json={"refresh": current})).status_code == 401

    async def test_concurrent_refreshes_with_one_token_cannot_both_succeed(self, api, ada):
        token = (await login(api))["refresh"]
        responses = await asyncio.gather(
            api.post(REFRESH, json={"refresh": token}), api.post(REFRESH, json={"refresh": token})
        )
        assert sorted(r.status_code for r in responses) == [200, 401]

    async def test_logout_is_idempotent_and_revokes(self, api, ada):
        tokens = await login(api)
        assert (await api.post(LOGOUT, json={"refresh": tokens["refresh"]})).status_code == 204
        assert (await api.post(LOGOUT, json={"refresh": tokens["refresh"]})).status_code == 204
        assert (await api.post(LOGOUT, json={"refresh": "garbage"})).status_code == 204
        assert (await api.post(REFRESH, json={"refresh": tokens["refresh"]})).status_code == 401

    async def test_expired_access_token_is_rejected(self, api, ada, settings):
        settings.access_token_ttl_seconds = -1
        expired = (await login(api))["access"]
        response = await api.get(ME, headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401

    async def test_refresh_tokens_are_stored_hashed(self, api, ada, app):
        from sqlalchemy import text

        refresh = (await login(api))["refresh"]
        async with app.state.engine.connect() as connection:
            stored = (
                (await connection.execute(text("SELECT token_hash FROM refresh_tokens")))
                .scalars()
                .all()
            )
        assert refresh not in stored
        assert all(len(value) == 64 for value in stored)


@pytest.mark.parametrize(
    ("value", "code"),
    [("a\x00b", "null_characters_not_allowed"), ("a\ud800b", "surrogate_characters_not_allowed")],
)
async def test_unstorable_characters_are_422_not_500(api, value, code):
    """Found by Schemathesis: a NUL byte in the login email crashed the database call."""
    # Raw JSON: json.dumps escapes NUL and unpaired surrogates (ensure_ascii),
    # which the client's own encoder refuses to send.
    response = await api.post(
        TOKEN,
        content=json.dumps({"email": value, "password": "x"}),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == code


async def test_wrong_json_type_is_rejected_not_coerced(api):
    response = await api.post(LOGOUT, json={"refresh": 0})
    assert response.status_code == 422
    assert response.json()["errors"][0] == {
        "field": "refresh",
        "code": "invalid",
        "message": "Input should be a valid string",
    }
