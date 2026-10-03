from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import emails
from apps.accounts.firebase import FirebaseIdentity
from apps.accounts.models import User, normalize_email
from apps.accounts.tokens import (
    email_verification_tokens,
    password_reset_tokens,
    user_from_link_token,
)
from apps.core.errors import ConflictError


def register_user(*, email: str, password: str, display_name: str) -> User:
    email = normalize_email(email)
    user = User(email=email, display_name=display_name.strip())
    try:
        # Runs Django's configured validators (length, common passwords,
        # similarity to the email/name, all-numeric).
        validate_password(password, user=user)
    except ValidationError as exc:
        # Keep each validator's own code (password_too_short, password_too_common, ...).
        raise ValidationError({"password": exc.error_list}) from None

    # Check-then-insert is racy: two requests can both pass the check. The
    # unique constraint is the real guard; the check gives the common case a
    # friendly field error, and IntegrityError covers the race.
    if User.objects.filter(email=email).exists():
        raise _duplicate_email()
    user.set_password(password)
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        raise _duplicate_email() from None
    return user


def _duplicate_email() -> ValidationError:
    # With a dict, Django ignores a top-level `code`; it must be on the inner error.
    return ValidationError(
        {"email": ValidationError("An account with this email already exists.", code="unique")}
    )


def _validated_password(password: str, user: User, field: str = "password") -> None:
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise ValidationError({field: exc.error_list}) from None


def token_pair(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def revoke_all_sessions(user: User) -> None:
    """Blacklist every refresh token the user holds: "sign out everywhere".

    Access tokens are stateless and stay valid until they expire (at most
    15 minutes). That window is the price of not checking a database on
    every request; keep access tokens short-lived.
    """
    outstanding = OutstandingToken.objects.filter(user=user)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding], ignore_conflicts=True
    )


# --- Firebase ---------------------------------------------------------------


@transaction.atomic
def user_for_firebase_identity(identity: FirebaseIdentity) -> User:
    """Map a *verified* Firebase identity to a local user.

    1. Already linked (same uid)      -> that user.
    2. Same email, verified by Firebase -> link the existing account.
    3. Same email, NOT verified        -> 409. Otherwise anyone could create a
       Firebase account with a victim's address and walk into their account.
    4. No match                        -> create a user (phone-only users have no email).
    """
    user = User.objects.select_for_update().filter(firebase_uid=identity.uid).first()
    if user is not None:
        if not user.is_active:
            raise AuthenticationFailed("No active account found with the given credentials")
        return user

    email = normalize_email(identity.email) if identity.email else None
    existing = User.objects.select_for_update().filter(email=email).first() if email else None
    if existing is not None:
        if not identity.email_verified:
            raise ConflictError(
                "An account with this email already exists. Verify the email with your "
                "sign-in provider, then try again."
            )
        if existing.firebase_uid is not None:
            raise ConflictError("This account is already linked to another sign-in.")
        if not existing.is_active:
            raise AuthenticationFailed("No active account found with the given credentials")
        existing.firebase_uid = identity.uid
        existing.email_verified = True
        existing.save(update_fields=["firebase_uid", "email_verified"])
        return existing

    display_name = identity.name or (email.split("@")[0] if email else "New user")
    try:
        with transaction.atomic():
            return User.objects.create_user(
                email,
                None,  # unusable password: this account signs in through Firebase
                display_name=display_name[:100],
                firebase_uid=identity.uid,
                email_verified=identity.email_verified,
            )
    except IntegrityError:
        # A concurrent first sign-in with the same uid won the race.
        return User.objects.get(firebase_uid=identity.uid)


# --- Passwords ----------------------------------------------------------------


@transaction.atomic
def change_password(*, user: User, current_password: str, new_password: str) -> None:
    if not user.check_password(current_password):
        raise ValidationError(
            {
                "current_password": ValidationError(
                    "The current password is incorrect.", code="incorrect"
                )
            }
        )
    _validated_password(new_password, user, field="new_password")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    revoke_all_sessions(user)


def request_password_reset(*, email: str) -> None:
    # Same response and (roughly) the same work either way: no account discovery.
    user = User.objects.filter(email=normalize_email(email), is_active=True).first()
    if user is not None and user.has_usable_password():
        emails.send_password_reset(user)


@transaction.atomic
def confirm_password_reset(*, token: str, password: str) -> None:
    user = user_from_link_token(password_reset_tokens, token)
    if user is None:
        raise ValidationError(
            {"token": ValidationError("This link is invalid or has expired.", code="invalid")}
        )
    _validated_password(password, user)
    user.set_password(password)  # changes the hash -> the token stops working
    user.save(update_fields=["password"])
    revoke_all_sessions(user)


# --- Email verification -------------------------------------------------------


def request_email_verification(*, user: User) -> None:
    if user.email and not user.email_verified:
        emails.send_email_verification(user)


def confirm_email_verification(*, token: str) -> None:
    user = user_from_link_token(email_verification_tokens, token)
    if user is None:
        raise ValidationError(
            {"token": ValidationError("This link is invalid or has expired.", code="invalid")}
        )
    user.email_verified = True  # changes the hashed state -> the token stops working
    user.save(update_fields=["email_verified"])
