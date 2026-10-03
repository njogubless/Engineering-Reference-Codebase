"""Auth use cases. Each function owns its transaction (explicit commit)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.firebase import FirebaseIdentity
from app.auth.models import RefreshToken, User
from app.auth.schemas import RegisterRequest, TokenPair
from app.auth.security import (
    create_access_token,
    create_link_token,
    hash_password,
    hash_refresh_secret,
    new_refresh_secret,
    password_problems,
    read_link_token,
    state_fingerprint,
    verify_password,
)
from app.core.config import Settings
from app.core.email import EmailMessage, EmailSender
from app.core.errors import AuthenticationError, ConflictError, ValidationFailedError
from app.core.ids import uuid7

INVALID_CREDENTIALS = "No active account found with the given credentials"
INVALID_REFRESH = "Token is invalid or expired"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _duplicate_email() -> ValidationFailedError:
    return ValidationFailedError.field(
        "email", "unique", "An account with this email already exists."
    )


async def register(session: AsyncSession, data: RegisterRequest, settings: Settings) -> User:
    email = normalize_email(data.email)
    problems = password_problems(data.password, email=email, display_name=data.display_name)
    if problems:
        raise ValidationFailedError(problems)
    # Friendly check first; the unique index is the real guard against races.
    if await session.scalar(select(User.id).where(User.email == email)):
        raise _duplicate_email()
    user = User(
        email=email,
        password_hash=hash_password(data.password, settings),
        display_name=data.display_name,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise _duplicate_email() from None
    return user


async def authenticate(
    session: AsyncSession, email: str, password: str, settings: Settings
) -> User:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))
    # verify_password runs even when the user does not exist (equal timing).
    password_ok = verify_password(password, user.password_hash if user else None, settings)
    if user is None or not password_ok or not user.is_active:
        raise AuthenticationError(INVALID_CREDENTIALS)
    return user


async def issue_tokens(
    session: AsyncSession, user_id: UUID, settings: Settings, family_id: UUID | None = None
) -> TokenPair:
    token, token_hash = new_refresh_secret()
    session.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid7(),
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    await session.commit()
    return TokenPair(access=create_access_token(user_id, settings), refresh=token)


async def rotate(session: AsyncSession, refresh: str, settings: Settings) -> TokenPair:
    # FOR UPDATE: two concurrent refreshes with the same token are serialised,
    # so only one of them can rotate it (the other sees it revoked).
    stored = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_secret(refresh))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if stored is None or stored.expires_at <= now:
        raise AuthenticationError(INVALID_REFRESH)
    if stored.revoked_at is not None:
        # Reuse of a rotated token: assume theft and revoke the whole family.
        await _revoke_family(session, stored.family_id, now)
        await session.commit()
        raise AuthenticationError(INVALID_REFRESH)
    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(INVALID_REFRESH)
    stored.revoked_at = now
    return await issue_tokens(session, stored.user_id, settings, family_id=stored.family_id)


async def logout(session: AsyncSession, refresh: str) -> None:
    """Revoke the session (the token's family). Unknown tokens are a no-op: idempotent."""
    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_secret(refresh))
    )
    if stored is not None:
        await _revoke_family(session, stored.family_id, datetime.now(UTC))
        await session.commit()


async def _revoke_family(session: AsyncSession, family_id: UUID, now: datetime) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


# --- Sessions -------------------------------------------------------------------


async def revoke_all_sessions(session: AsyncSession, user_id: UUID) -> None:
    """ "Sign out everywhere": revoke every refresh token of the user. Access
    tokens stay valid until they expire (at most 15 minutes)."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


# --- Firebase ---------------------------------------------------------------------


async def user_for_firebase_identity(session: AsyncSession, identity: FirebaseIdentity) -> User:
    """Same rules as the Django API: linked uid -> that user; same email and
    verified by Firebase -> link; same email unverified -> 409 (takeover
    guard); otherwise create (phone-only users have no email)."""
    user = await session.scalar(
        select(User).where(User.firebase_uid == identity.uid).with_for_update()
    )
    if user is not None:
        if not user.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)
        return user

    email = normalize_email(identity.email) if identity.email else None
    existing = (
        await session.scalar(select(User).where(User.email == email).with_for_update())
        if email
        else None
    )
    if existing is not None:
        if not identity.email_verified:
            raise ConflictError(
                "An account with this email already exists. Verify the email with your "
                "sign-in provider, then try again."
            )
        if existing.firebase_uid is not None:
            raise ConflictError("This account is already linked to another sign-in.")
        if not existing.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)
        existing.firebase_uid = identity.uid
        existing.email_verified = True
        await session.commit()
        return existing

    display_name = identity.name or (email.split("@")[0] if email else "New user")
    user = User(
        email=email,
        password_hash=None,  # this account signs in through Firebase
        display_name=display_name[:100],
        firebase_uid=identity.uid,
        email_verified=identity.email_verified,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # A concurrent first sign-in with the same uid won the race.
        await session.rollback()
        winner = await session.scalar(select(User).where(User.firebase_uid == identity.uid))
        if winner is None:
            raise
        return winner
    return user


# --- Passwords --------------------------------------------------------------------


def _reset_fingerprint(user: User) -> str:
    return state_fingerprint(user.password_hash, user.is_active)


def _verification_fingerprint(user: User) -> str:
    return state_fingerprint(user.email, user.email_verified)


async def change_password(
    session: AsyncSession, user: User, current: str, new: str, settings: Settings
) -> TokenPair:
    if not verify_password(current, user.password_hash, settings):
        raise ValidationFailedError.field(
            "current_password", "incorrect", "The current password is incorrect."
        )
    problems = password_problems(new, email=user.email or "", display_name=user.display_name)
    if problems:
        raise ValidationFailedError(
            [replace(problem, field="new_password") for problem in problems]
        )
    user.password_hash = hash_password(new, settings)
    await revoke_all_sessions(session, user.id)
    return await issue_tokens(session, user.id, settings)  # commits


async def request_password_reset(
    session: AsyncSession,
    email: str,
    settings: Settings,
    background: BackgroundTasks,
    sender: EmailSender,
) -> None:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))
    # Same 202 either way; sending happens after the response, so the response
    # time does not reveal whether the account exists.
    if user is None or not user.is_active or user.password_hash is None or user.email is None:
        return
    token = create_link_token(
        purpose="password_reset",
        user_id=user.id,
        fingerprint=_reset_fingerprint(user),
        ttl_seconds=settings.password_reset_ttl_seconds,
        settings=settings,
    )
    link = f"{settings.frontend_base_url.rstrip('/')}/reset-password?{urlencode({'token': token})}"
    background.add_task(
        sender.send,
        EmailMessage(
            to=user.email,
            subject="Reset your password",
            body=(
                f"Someone asked to reset the password for this account.\n\n{link}\n\n"
                "The link works once and expires in one hour. If it wasn't you, ignore this email."
            ),
        ),
    )


async def _user_from_link(
    session: AsyncSession, token: str, purpose: str, settings: Settings
) -> User | None:
    read = read_link_token(token, purpose=purpose, settings=settings)
    if read is None:
        return None
    user_id, fingerprint = read
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        return None
    current = (
        _reset_fingerprint(user) if purpose == "password_reset" else _verification_fingerprint(user)
    )
    return user if current == fingerprint else None


_INVALID_LINK = ValidationFailedError.field(
    "token", "invalid", "This link is invalid or has expired."
)


async def confirm_password_reset(
    session: AsyncSession, token: str, password: str, settings: Settings
) -> None:
    user = await _user_from_link(session, token, "password_reset", settings)
    if user is None:
        raise _INVALID_LINK
    problems = password_problems(password, email=user.email or "", display_name=user.display_name)
    if problems:
        raise ValidationFailedError(problems)
    user.password_hash = hash_password(password, settings)  # new hash -> the token stops working
    await revoke_all_sessions(session, user.id)
    await session.commit()


# --- Email verification ---------------------------------------------------------


def request_email_verification(
    user: User, settings: Settings, background: BackgroundTasks, sender: EmailSender
) -> None:
    if user.email is None or user.email_verified:
        return
    token = create_link_token(
        purpose="verify_email",
        user_id=user.id,
        fingerprint=_verification_fingerprint(user),
        ttl_seconds=settings.email_verification_ttl_seconds,
        settings=settings,
    )
    link = f"{settings.frontend_base_url.rstrip('/')}/verify-email?{urlencode({'token': token})}"
    background.add_task(
        sender.send,
        EmailMessage(
            to=user.email,
            subject="Confirm your email address",
            body=f"Confirm this address:\n\n{link}",
        ),
    )


async def confirm_email_verification(session: AsyncSession, token: str, settings: Settings) -> None:
    user = await _user_from_link(session, token, "verify_email", settings)
    if user is None:
        raise _INVALID_LINK
    user.email_verified = True  # changes the fingerprinted state -> single use
    await session.commit()
