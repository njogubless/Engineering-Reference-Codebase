"""Write use cases. Plain functions, keyword-only arguments, no base class.

Authorization (who may edit) is enforced by the view's permission classes;
these functions enforce the domain rules that hold whoever calls them.
"""

from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Comment, Post


def _apply_status(post: Post, status: str) -> None:
    post.status = status
    if status == Post.Status.PUBLISHED:
        post.published_at = post.published_at or timezone.now()
    else:
        post.published_at = None


def create_post(
    *, author: User, title: str, body: str = "", status: str = Post.Status.DRAFT
) -> Post:
    post = Post(author=author, title=title.strip(), body=body)
    _apply_status(post, status)
    post.save()
    return post


def update_post(*, post: Post, changes: dict[str, Any]) -> Post:
    if not changes:
        raise ValidationError("No fields to update.", code="empty_update")
    if "title" in changes:
        post.title = changes["title"].strip()
    if "body" in changes:
        post.body = changes["body"]
    if "status" in changes:
        _apply_status(post, changes["status"])
    post.save()
    return post


def delete_post(*, post: Post) -> None:
    post.delete()  # comments go with it (on_delete=CASCADE)


def create_comment(*, post: Post, author: User, body: str) -> Comment:
    if post.status != Post.Status.PUBLISHED:
        raise ValidationError("Drafts cannot be commented on.", code="post_not_published")
    return Comment.objects.create(post=post, author=author, body=body.strip())


def delete_comment(*, comment: Comment) -> None:
    comment.delete()
