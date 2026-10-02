"""Seed demo data for the client demos: `python manage.py seed_demo`.

Idempotent: running it twice does not duplicate anything.
"""

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.posts.models import Comment, Post

DEMO_USERS = [
    ("ada@example.com", "Ada"),
    ("grace@example.com", "Grace"),
]
DEMO_PASSWORD = "demo-password-123"  # noqa: S105 - documented demo credential, local data only


class Command(BaseCommand):
    help = "Create demo users, published posts and comments (idempotent)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        users = []
        for email, name in DEMO_USERS:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email, DEMO_PASSWORD, display_name=name)
            users.append(user)

        if Post.objects.filter(author__in=users).exists():
            self.stdout.write("Demo data already present.")
            return

        now = timezone.now()
        for index in range(45):
            created = now - timedelta(hours=index)
            post = Post.objects.create(
                author=users[index % 2],
                title=f"Demo post {index + 1}",
                body=f"Body of demo post {index + 1}.",
                status=Post.Status.PUBLISHED,
                published_at=created,
                created_at=created,
            )
            for number in range(index % 4):
                Comment.objects.create(
                    post=post, author=users[(index + number + 1) % 2], body=f"Comment {number + 1}"
                )
        self.stdout.write(
            self.style.SUCCESS(f"Seeded 45 posts. Sign in as {DEMO_USERS[0][0]} / {DEMO_PASSWORD}")
        )
