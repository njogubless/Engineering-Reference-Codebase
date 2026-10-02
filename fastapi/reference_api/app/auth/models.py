from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import uuid7


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Case-insensitive uniqueness, guarding even writes that skip normalisation.
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)
    date_joined: Mapped[datetime] = mapped_column(default=utcnow)


class RefreshToken(Base):
    """One row per issued refresh token.

    - Only a SHA-256 hash is stored: a leaked database does not leak usable tokens.
    - `family_id` links every token rotated from one login. Presenting an
      already-rotated token means it was stolen (or replayed), so the whole
      family is revoked: the attacker and the victim are both logged out, and
      the attacker's copy stops working.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
