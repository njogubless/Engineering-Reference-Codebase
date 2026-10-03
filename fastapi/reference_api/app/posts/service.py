"""Posts use cases.

Visibility vs permission, as in the Django API:
- not visible to the requester -> 404 (other users' drafts must not leak)
- visible but not theirs to change -> 403
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.models import User
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationFailedError
from app.core.pagination import PageParams, Position, encode_cursor
from app.posts.models import Comment, Post, PostStatus
from app.posts.schemas import AuthorOut, CommentCreate, CommentOut, PostCreate, PostOut, PostUpdate

_comment_count = (
    select(func.count(Comment.id))
    .where(Comment.post_id == Post.id)
    .correlate(Post)
    .scalar_subquery()
)


def _posts() -> Select[Post, int]:
    """Post + author (joined) + comment count (subquery): one query per page, no N+1."""
    return select(Post, _comment_count.label("comment_count")).options(joinedload(Post.author))


def to_post_out(post: Post, comment_count: int) -> PostOut:
    return PostOut(
        id=post.id,
        title=post.title,
        body=post.body,
        status=post.status,
        author=AuthorOut(id=post.author.id, display_name=post.author.display_name),
        comment_count=comment_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
        published_at=post.published_at,
    )


async def list_published(
    session: AsyncSession, page: PageParams
) -> tuple[list[PostOut], str | None]:
    query = _posts().where(Post.status == "published")
    if page.position:
        query = query.where(
            tuple_(Post.created_at, Post.id) < tuple_(page.position.created_at, page.position.id)
        )
    rows = (
        await session.execute(
            query.order_by(Post.created_at.desc(), Post.id.desc()).limit(page.limit + 1)
        )
    ).all()
    return _page([to_post_out(post, count) for post, count in rows], page.limit)


async def get_visible(session: AsyncSession, post_id: UUID, user: User | None) -> PostOut:
    post, count = await _get_visible_row(session, post_id, user)
    return to_post_out(post, count)


async def _get_visible_row(
    session: AsyncSession, post_id: UUID, user: User | None
) -> tuple[Post, int]:
    visible = Post.status == "published"
    if user is not None:
        visible = or_(visible, Post.author_id == user.id)
    row = (await session.execute(_posts().where(Post.id == post_id, visible))).first()
    if row is None:
        raise NotFoundError("No post exists with this id.")
    return row[0], row[1]


def _ensure_author(owner_id: UUID, user: User) -> None:
    if owner_id != user.id:
        raise PermissionDeniedError("Only the author can change this.")


def _apply_status(post: Post, status: PostStatus) -> None:
    post.status = status
    post.published_at = (post.published_at or datetime.now(UTC)) if status == "published" else None


async def create(session: AsyncSession, author: User, data: PostCreate) -> PostOut:
    post = Post(author_id=author.id, title=data.title, body=data.body)
    _apply_status(post, data.status)
    session.add(post)
    await session.commit()
    return await get_visible(session, post.id, author)


async def update(session: AsyncSession, post_id: UUID, user: User, data: PostUpdate) -> PostOut:
    post, _ = await _get_visible_row(session, post_id, user)
    _ensure_author(post.author_id, user)
    changes: dict[str, Any] = data.model_dump(exclude_unset=True)
    if not changes:
        raise ValidationFailedError.field(None, "empty_update", "No fields to update.")
    if "title" in changes:
        post.title = changes["title"]
    if "body" in changes:
        post.body = changes["body"]
    if "status" in changes:
        _apply_status(post, changes["status"])
    await session.commit()
    return await get_visible(session, post.id, user)


async def delete(session: AsyncSession, post_id: UUID, user: User) -> None:
    post, _ = await _get_visible_row(session, post_id, user)
    _ensure_author(post.author_id, user)
    await session.delete(post)  # comments are removed by ON DELETE CASCADE
    await session.commit()


async def list_comments(
    session: AsyncSession, post_id: UUID, user: User | None, page: PageParams
) -> tuple[list[CommentOut], str | None]:
    await _get_visible_row(session, post_id, user)
    query = select(Comment).options(joinedload(Comment.author)).where(Comment.post_id == post_id)
    if page.position:
        query = query.where(
            tuple_(Comment.created_at, Comment.id)
            > tuple_(page.position.created_at, page.position.id)
        )
    comments = (
        await session.scalars(query.order_by(Comment.created_at, Comment.id).limit(page.limit + 1))
    ).all()
    return _page([CommentOut.model_validate(c) for c in comments], page.limit)


async def create_comment(
    session: AsyncSession, post_id: UUID, user: User, data: CommentCreate
) -> CommentOut:
    post, _ = await _get_visible_row(session, post_id, user)
    if post.status != "published":
        raise ValidationFailedError.field(
            None, "post_not_published", "Drafts cannot be commented on."
        )
    comment = Comment(post_id=post.id, author_id=user.id, body=data.body)
    session.add(comment)
    await session.commit()
    created = await session.scalar(
        select(Comment).options(joinedload(Comment.author)).where(Comment.id == comment.id)
    )
    return CommentOut.model_validate(created)


async def delete_comment(
    session: AsyncSession, post_id: UUID, comment_id: UUID, user: User
) -> None:
    await _get_visible_row(session, post_id, user)
    comment = await session.scalar(
        select(Comment).where(Comment.id == comment_id, Comment.post_id == post_id)
    )
    if comment is None:
        raise NotFoundError("No comment exists with this id on this post.")
    _ensure_author(comment.author_id, user)
    await session.delete(comment)
    await session.commit()


def _page[T: (PostOut, CommentOut)](items: list[T], limit: int) -> tuple[list[T], str | None]:
    if len(items) <= limit:
        return items, None
    items = items[:limit]
    last = items[-1]
    return items, encode_cursor(Position(created_at=last.created_at, id=last.id))
