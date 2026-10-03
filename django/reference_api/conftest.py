"""Shared fixtures. Plain functions over factory libraries: the models are small."""

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.services import create_post

PASSWORD = "correct-horse-battery"  # noqa: S105 - test credential


@pytest.fixture
def make_user(db: Any) -> Callable[..., User]:
    counter = iter(range(1, 10_000))

    def make(email: str | None = None, display_name: str = "User") -> User:
        return User.objects.create_user(
            email or f"user{next(counter)}@example.com", PASSWORD, display_name=display_name
        )

    return make


@pytest.fixture
def user(make_user: Callable[..., User]) -> User:
    return make_user("ada@example.com", "Ada")


@pytest.fixture
def other_user(make_user: Callable[..., User]) -> User:
    return make_user("grace@example.com", "Grace")


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def client_as() -> Callable[[User], APIClient]:
    """An API client authenticated as the given user (bypasses token issuing)."""

    def make(user: User) -> APIClient:
        api = APIClient()
        api.force_authenticate(user)
        return api

    return make


@pytest.fixture
def make_post(user: User) -> Callable[..., Post]:
    def make(
        author: User | None = None, status: str = Post.Status.PUBLISHED, **fields: Any
    ) -> Post:
        return create_post(
            author=author or user, title=fields.pop("title", "A title"), status=status, **fields
        )

    return make
