"""Firebase ID tokens from the real Auth emulator, verified by firebase-admin.
Run with `make check-firebase` (starts the emulator around the tests)."""

import time

import pytest
from firebase_admin import auth as firebase_auth

from apps.accounts.firebase import _app
from apps.accounts.models import User
from apps.accounts.tests import emulator
from conftest import PASSWORD

pytestmark = [pytest.mark.firebase, pytest.mark.django_db]

EXCHANGE = "/api/v1/auth/firebase"


@pytest.fixture(autouse=True)
def clean_emulator():
    emulator.reset()
    yield
    emulator.reset()


def exchange(client, id_token):
    return client.post(EXCHANGE, {"id_token": id_token}, format="json")


def test_a_real_id_token_becomes_api_tokens_for_a_new_user(client):
    signed_up = emulator.sign_up("new@example.com", "firebase-password")
    response = exchange(client, signed_up["idToken"])
    assert response.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    me = client.get("/api/v1/auth/me").json()
    assert me["email"] == "new@example.com"
    assert me["email_verified"] is False
    assert User.objects.get(email="new@example.com").firebase_uid == signed_up["localId"]


def test_a_token_for_another_project_is_rejected(client):
    token = emulator.sign_up("x@example.com", "firebase-password")["idToken"]
    forged = emulator.with_claim(token, aud="demo-someone-else")
    assert exchange(client, forged).status_code == 401


def test_a_tampered_identity_is_rejected(client):
    """The emulator does not sign tokens, so this forgery passes the signature
    step here (in production it would fail it). It must still be a 401, never
    a 500: the revocation check finds no such user."""
    token = emulator.sign_up("x@example.com", "firebase-password")["idToken"]
    forged = emulator.with_claim(token, sub="someone-else", user_id="someone-else")
    assert exchange(client, forged).status_code == 401


def test_disabled_firebase_users_are_rejected(client):
    signed_up = emulator.sign_up("x@example.com", "firebase-password")
    firebase_auth.update_user(signed_up["localId"], disabled=True, app=_app())
    assert exchange(client, signed_up["idToken"]).status_code == 401


def test_revoked_tokens_are_rejected(client):
    signed_up = emulator.sign_up("x@example.com", "firebase-password")
    time.sleep(1.1)  # revocation has one-second resolution
    firebase_auth.revoke_refresh_tokens(signed_up["localId"], app=_app())
    assert exchange(client, signed_up["idToken"]).status_code == 401


def test_verified_firebase_email_links_the_existing_password_account(client, user):
    signed_up = emulator.sign_up("ada@example.com", "firebase-password")
    firebase_auth.update_user(signed_up["localId"], email_verified=True, app=_app())
    fresh = emulator.sign_in("ada@example.com", "firebase-password")  # new token carries the claim
    assert exchange(client, fresh["idToken"]).status_code == 200
    user.refresh_from_db()
    assert user.firebase_uid == signed_up["localId"]
    assert user.check_password(PASSWORD)  # the password login keeps working


def test_unverified_firebase_email_cannot_take_over_an_account(client, user):
    token = emulator.sign_up("ada@example.com", "firebase-password")["idToken"]
    response = exchange(client, token)
    assert response.status_code == 409
    user.refresh_from_db()
    assert user.firebase_uid is None


def test_phone_sign_in_creates_a_user_without_email(client):
    signed_in = emulator.phone_sign_in("+254700000001")
    assert exchange(client, signed_in["idToken"]).status_code == 200
    assert User.objects.get(firebase_uid=signed_in["localId"]).email is None
