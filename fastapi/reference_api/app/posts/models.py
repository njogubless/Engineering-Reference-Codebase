"""Posts and comments. Same rules as the Django models, enforced by the database."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import User, utcnow
from app.core.db import Base
from app.core.ids import uuid7

PostStatus = Literal["draft", "published"]


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("title <> ''", name="title_not_blank"),
        CheckConstraint("status IN ('draft', 'published')", name="status_valid"),
        # published <=> published_at is set
        CheckConstraint(
            "(status = 'draft' AND published_at IS NULL)"
            " OR (status = 'published' AND published_at IS NOT NULL)",
            name="published_at_matches_status",
        ),
        # Partial index for the public listing, in keyset order.
        Index(
            "ix_posts_published_recent",
            text("created_at DESC"),
            text("id DESC"),
            postgresql_where=text("status = 'published'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[PostStatus] = mapped_column(String(10), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # lazy="raise": touching an unloaded relationship is an error, not a hidden
    # query. In async SQLAlchemy an implicit lazy load would fail anyway; this
    # makes every N+1 impossible by construction — loads must be explicit.
    author: Mapped[User] = relationship(lazy="raise")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("body <> ''", name="body_not_blank"),
        Index("ix_comments_post_order", "post_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    author: Mapped[User] = relationship(lazy="raise")
