"""Real emulator ID tokens, verified by firebase-admin. Run with `make check-firebase`."""

import asyncio

import httpx2
import pytest
from firebase_admin import auth as firebase_auth

from app.auth.firebase import firebase_app
from tests.conftest import signup
from tests.firebase import emulator

pytestmark = pytest.mark.firebase

EXCHANGE = "/api/v1/auth/firebase"


@pytest.fixture(autouse=True)
def clean_emulator():
    emulator.reset()
    yield
    emulator.reset()


def admin():
    return firebase_app("demo-reference")


async def exchange(api: httpx2.AsyncClient, token: str) -> httpx2.Response:
    return await api.post(EXCHANGE, json={"id_token": token})


async def test_a_real_id_token_becomes_api_tokens(api):
    signed_up = emulator.sign_up("new@example.com", "firebase-password")
    response = await exchange(api, signed_up["idToken"])
    assert response.status_code == 200
    me = await api.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {response.json()['access']}"}
    )
    assert me.json()["email"] == "new@example.com"
    assert me.json()["email_verified"] is False


async def test_foreign_audience_and_tampered_subject_are_rejected(api):
    token = emulator.sign_up("x@example.com", "firebase-password")["idToken"]
    assert (
        await exchange(api, emulator.with_claim(token, aud="demo-someone-else"))
    ).status_code == 401
    assert (
        await exchange(api, emulator.with_claim(token, sub="other", user_id="other"))
    ).status_code == 401


async def test_disabled_and_revoked_users_are_rejected(api):
    disabled = emulator.sign_up("d@example.com", "firebase-password")
    firebase_auth.update_user(disabled["localId"], disabled=True, app=admin())
    assert (await exchange(api, disabled["idToken"])).status_code == 401

    revoked = emulator.sign_up("r@example.com", "firebase-password")
    await asyncio.sleep(1.1)  # revocation has one-second resolution
    firebase_auth.revoke_refresh_tokens(revoked["localId"], app=admin())
    assert (await exchange(api, revoked["idToken"])).status_code == 401


async def test_verified_email_links_and_unverified_conflicts(api):
    await signup(api, "ada@example.com", "Ada")
    unverified = emulator.sign_up("ada@example.com", "firebase-password")
    assert (await exchange(api, unverified["idToken"])).status_code == 409

    firebase_auth.update_user(unverified["localId"], email_verified=True, app=admin())
    fresh = emulator.sign_in("ada@example.com", "firebase-password")
    assert (await exchange(api, fresh["idToken"])).status_code == 200


async def test_phone_sign_in(api):
    signed_in = emulator.phone_sign_in("+254700000002")
    response = await exchange(api, signed_in["idToken"])
    assert response.status_code == 200
    me = await api.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {response.json()['access']}"}
    )
    assert me.json()["email"] is None
