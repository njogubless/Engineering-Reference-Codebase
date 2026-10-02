"""Read queries. Views never build querysets themselves.

Every queryset that is serialized with its author uses select_related, and
comment counts come from one annotated query, so a page costs a fixed number
of queries however many rows it has (tests assert the exact count).
"""

from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.db.models import Count, Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.posts.models import Comment, Post


def _posts() -> QuerySet[Post]:
    return Post.objects.select_related("author").annotate(comment_count=Count("comments"))


def published_posts() -> QuerySet[Post]:
    return _posts().filter(status=Post.Status.PUBLISHED)


def get_visible_post(post_id: UUID, user: User | AnonymousUser) -> Post:
    """A published post, or the user's own draft. Anything else is a 404 —
    including other users' drafts, whose existence must not leak."""
    visible = Q(status=Post.Status.PUBLISHED)
    if user.is_authenticated:
        visible |= Q(author=user)
    try:
        return _posts().get(visible, pk=post_id)
    except Post.DoesNotExist:
        raise Http404 from None


def post_comments(post: Post) -> QuerySet[Comment]:
    return Comment.objects.filter(post=post).select_related("author")


def get_comment(post: Post, comment_id: UUID) -> Comment:
    try:
        return post_comments(post).get(pk=comment_id)
    except Comment.DoesNotExist:
        raise Http404 from None
