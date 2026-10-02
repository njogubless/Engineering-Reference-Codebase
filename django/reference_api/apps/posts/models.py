"""Posts and comments: the resource used to demonstrate CRUD, ownership and pagination.

Rules live in the database as well as in code. Constraints are the last line
of defence: they hold even for writes that bypass the service layer (shell,
data migrations, a future second service).
"""

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.ids import uuid7


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(condition=~Q(title=""), name="posts_post_title_not_blank"),
            models.CheckConstraint(
                condition=Q(status__in=["draft", "published"]), name="posts_post_status_valid"
            ),
            # published <=> published_at is set. Without this, a bug could
            # create "published" posts with no date that sort unpredictably.
            models.CheckConstraint(
                condition=Q(status="draft", published_at__isnull=True)
                | Q(status="published", published_at__isnull=False),
                name="posts_post_published_at_matches_status",
            ),
        ]
        indexes: ClassVar = [
            # Partial index for the public listing: only published rows, in
            # exactly the order the cursor paginator reads them.
            models.Index(
                fields=["-created_at", "-id"],
                condition=Q(status="published"),
                name="posts_published_recent_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(condition=~Q(body=""), name="posts_comment_body_not_blank"),
        ]
        indexes: ClassVar = [
            # Serves "comments of post X, oldest first" without a sort step.
            models.Index(fields=["post", "created_at", "id"], name="posts_comment_post_order_idx"),
        ]

    def __str__(self) -> str:
        return f"Comment {self.id} on {self.post_id}"
