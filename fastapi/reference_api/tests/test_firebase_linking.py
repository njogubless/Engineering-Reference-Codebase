"""Account-linking rules (no emulator: identities as verify_id_token returns them)."""

import httpx2
import pytest
from fastapi import FastAPI

from app.auth import service
from app.auth.firebase import FirebaseIdentity
from app.core.errors import AuthenticationError, ConflictError
from tests.conftest import signup


def identity(uid="fb-1", email="ada@example.com", verified=True, name="Ada") -> FirebaseIdentity:
    return FirebaseIdentity(uid=uid, email=email, email_verified=verified, name=name)


@pytest.fixture
async def link(app: FastAPI, api: httpx2.AsyncClient):
    async def run(value: FirebaseIdentity):
        async with app.state.sessionmaker() as session:
            return await service.user_for_firebase_identity(session, value)

    return run


async def test_first_sign_in_creates_a_passwordless_user(link):
    user = await link(identity())
    assert user.firebase_uid == "fb-1"
    assert user.email_verified is True
    assert user.password_hash is None


async def test_later_sign_ins_return_the_same_user(link):
    first = await link(identity())
    assert (await link(identity(email="changed@example.com"))).id == first.id


async def test_verified_email_links_an_existing_account(api, link):
    await signup(api, "ada@example.com", "Ada")
    linked = await link(identity(email="ADA@example.com"))
    assert linked.email == "ada@example.com"
    assert linked.firebase_uid == "fb-1"


async def test_unverified_email_never_links(api, link):
    await signup(api, "ada@example.com", "Ada")
    with pytest.raises(ConflictError):
        await link(identity(verified=False))


async def test_already_linked_accounts_are_not_relinked(api, link):
    await link(identity(uid="fb-other"))
    with pytest.raises(ConflictError):
        await link(identity(uid="fb-new"))


async def test_phone_only_users_have_no_email(link):
    first = await link(identity(uid="p1", email=None, verified=False, name=None))
    second = await link(identity(uid="p2", email=None, verified=False, name=None))
    assert first.email is None and second.email is None
    assert first.display_name == "New user"


async def test_firebase_only_accounts_cannot_use_password_login(api, link):
    await link(identity())
    response = await api.post(
        "/api/v1/auth/token", json={"email": "ada@example.com", "password": "anything"}
    )
    assert response.status_code == 401


async def test_the_endpoint_accepts_only_a_token(api):
    response = await api.post("/api/v1/auth/firebase", json={"id_token": "x", "uid": "victim"})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "uid"


async def test_inactive_linked_users_are_rejected(app, link):
    from sqlalchemy import text

    await link(identity())
    async with app.state.engine.begin() as connection:
        await connection.execute(text("UPDATE users SET is_active = false"))
    with pytest.raises(AuthenticationError):
        await link(identity())
