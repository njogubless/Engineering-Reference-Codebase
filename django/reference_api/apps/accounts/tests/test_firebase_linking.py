"""Account-linking rules for verified Firebase identities (no emulator needed:
these call the service with identities as `verify_id_token` would return them)."""

import pytest
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts import services
from apps.accounts.firebase import FirebaseIdentity
from apps.accounts.models import User
from apps.core.errors import ConflictError

pytestmark = pytest.mark.django_db


def identity(uid="fb-1", email="ada@example.com", verified=True, name="Ada"):
    return FirebaseIdentity(uid=uid, email=email, email_verified=verified, name=name)


def test_first_sign_in_creates_a_user_without_a_usable_password():
    user = services.user_for_firebase_identity(identity())
    assert user.firebase_uid == "fb-1"
    assert user.email == "ada@example.com"
    assert user.email_verified is True
    assert not user.has_usable_password()


def test_later_sign_ins_return_the_same_user():
    first = services.user_for_firebase_identity(identity())
    assert services.user_for_firebase_identity(identity(email="changed@example.com")) == first


def test_verified_email_links_an_existing_password_account(user):
    linked = services.user_for_firebase_identity(identity(email="ADA@example.com"))
    assert linked.pk == user.pk
    assert linked.firebase_uid == "fb-1"
    assert linked.email_verified is True


def test_unverified_email_never_links_an_existing_account(user):
    """Account takeover guard: anyone can create a Firebase account with a
    victim's address; until it is verified, it proves nothing."""
    with pytest.raises(ConflictError):
        services.user_for_firebase_identity(identity(verified=False))
    user.refresh_from_db()
    assert user.firebase_uid is None


def test_an_account_already_linked_elsewhere_is_not_relinked(user):
    user.firebase_uid = "fb-other"
    user.save()
    with pytest.raises(ConflictError):
        services.user_for_firebase_identity(identity(uid="fb-new"))


def test_phone_only_identities_create_users_without_email():
    user = services.user_for_firebase_identity(
        identity(uid="fb-phone", email=None, verified=False, name=None)
    )
    assert user.email is None
    assert user.display_name == "New user"
    # Several phone users can coexist: unique constraints allow many NULLs.
    services.user_for_firebase_identity(
        identity(uid="fb-phone-2", email=None, verified=False, name=None)
    )
    assert User.objects.filter(email__isnull=True).count() == 2


def test_deactivated_users_cannot_sign_in_with_firebase(user):
    user.firebase_uid = "fb-1"
    user.is_active = False
    user.save()
    with pytest.raises(AuthenticationFailed):
        services.user_for_firebase_identity(identity())


def test_the_endpoint_accepts_only_a_token(client):
    """No way to assert an identity: a uid or email in the body is rejected."""
    response = client.post(
        "/api/v1/auth/firebase", {"id_token": "x", "uid": "victim"}, format="json"
    )
    assert response.status_code == 422
    assert response.json()["errors"][0] == {
        "field": "uid",
        "code": "unknown_field",
        "message": "Unknown field.",
    }
