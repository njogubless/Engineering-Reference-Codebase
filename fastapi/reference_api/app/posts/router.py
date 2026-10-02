from uuid import UUID

from fastapi import APIRouter, Response, status

from app.auth.dependencies import CurrentUser, OptionalUser
from app.core.db import SessionDep
from app.core.pagination import PageDep
from app.posts import service
from app.posts.schemas import (
    CommentCreate,
    CommentOut,
    CommentPage,
    PostCreate,
    PostOut,
    PostPage,
    PostUpdate,
)

router = APIRouter(prefix="/api/v1/posts", tags=["posts"])


@router.get("", operation_id="listPosts")
async def list_posts(session: SessionDep, page: PageDep, user: OptionalUser) -> PostPage:
    items, next_cursor = await service.list_published(session, page)
    return PostPage(items=items, next_cursor=next_cursor)


@router.post("", operation_id="createPost", status_code=status.HTTP_201_CREATED)
async def create_post(data: PostCreate, session: SessionDep, user: CurrentUser) -> PostOut:
    return await service.create(session, user, data)


@router.get("/{post_id}", operation_id="getPost")
async def get_post(post_id: UUID, session: SessionDep, user: OptionalUser) -> PostOut:
    return await service.get_visible(session, post_id, user)


@router.patch("/{post_id}", operation_id="updatePost")
async def update_post(
    post_id: UUID, data: PostUpdate, session: SessionDep, user: CurrentUser
) -> PostOut:
    return await service.update(session, post_id, user, data)


@router.delete("/{post_id}", operation_id="deletePost", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: UUID, session: SessionDep, user: CurrentUser) -> Response:
    await service.delete(session, post_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{post_id}/comments", operation_id="listComments")
async def list_comments(
    post_id: UUID, session: SessionDep, page: PageDep, user: OptionalUser
) -> CommentPage:
    items, next_cursor = await service.list_comments(session, post_id, user, page)
    return CommentPage(items=items, next_cursor=next_cursor)


@router.post(
    "/{post_id}/comments", operation_id="createComment", status_code=status.HTTP_201_CREATED
)
async def create_comment(
    post_id: UUID, data: CommentCreate, session: SessionDep, user: CurrentUser
) -> CommentOut:
    return await service.create_comment(session, post_id, user, data)


@router.delete(
    "/{post_id}/comments/{comment_id}",
    operation_id="deleteComment",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    post_id: UUID, comment_id: UUID, session: SessionDep, user: CurrentUser
) -> Response:
    await service.delete_comment(session, post_id, comment_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
