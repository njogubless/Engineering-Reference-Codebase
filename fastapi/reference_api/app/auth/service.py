"""Auth use cases. Each function owns its transaction (explicit commit)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from app.auth.schemas import RegisterRequest, TokenPair
from app.auth.security import (
    create_access_token,
    hash_password,
    hash_refresh_secret,
    new_refresh_secret,
    password_problems,
    verify_password,
)
from app.core.config import Settings
from app.core.errors import AuthenticationError, ValidationFailedError
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
