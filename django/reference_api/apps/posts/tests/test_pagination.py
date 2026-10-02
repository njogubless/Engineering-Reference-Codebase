from datetime import timedelta

import pytest
from django.utils import timezone

from apps.posts.models import Comment, Post

pytestmark = pytest.mark.django_db

POSTS = "/api/v1/posts"


@pytest.fixture
def posts(user):
    now = timezone.now()
    # Five posts share one timestamp: ordering must still be total and stable.
    created = [now - timedelta(minutes=i // 5) for i in range(12)]
    return [
        Post.objects.create(
            author=user, title=f"p{i}", status="published", published_at=at, created_at=at
        )
        for i, at in enumerate(created)
    ]


def collect(client, url: str, limit: int) -> list[str]:
    ids: list[str] = []
    cursor = None
    while True:
        params = {"limit": limit, **({"cursor": cursor} if cursor else {})}
        page = client.get(url, params).json()
        ids += [item["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            return ids


def test_walking_all_pages_returns_every_post_once_newest_first(client, posts):
    ids = collect(client, POSTS, limit=5)
    expected = sorted(posts, key=lambda p: (p.created_at, p.id), reverse=True)
    assert ids == [str(p.id) for p in expected]


def test_a_post_created_while_paging_does_not_shift_later_pages(client, posts, user):
    first = client.get(POSTS, {"limit": 5}).json()
    newest = Post.objects.create(
        author=user, title="new", status="published", published_at=timezone.now()
    )
    second = client.get(POSTS, {"limit": 5, "cursor": first["next_cursor"]}).json()
    seen = [i["id"] for i in first["items"] + second["items"]]
    assert len(seen) == len(set(seen))  # no duplicates
    assert str(newest.id) not in seen


def test_last_page_has_null_cursor(client, posts):
    assert client.get(POSTS, {"limit": 100}).json()["next_cursor"] is None


@pytest.mark.parametrize("limit", ["0", "101", "abc", "-1"])
def test_invalid_limit_is_422_not_clamped(client, limit):
    response = client.get(POSTS, {"limit": limit})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "limit"


def test_tampered_cursor_is_422(client, posts):
    # base64("o=abc"): a cursor whose offset is not a number.
    response = client.get(POSTS, {"cursor": "bz1hYmM="})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "cursor"


def test_list_query_count_does_not_grow_with_page_size(
    client, posts, other_user, django_assert_num_queries
):
    for post in posts:
        Comment.objects.create(post=post, author=other_user, body="hi")
    # One query for the page (posts + authors joined + comment counts). No N+1.
    with django_assert_num_queries(1):
        client.get(POSTS, {"limit": 12})


def test_comment_list_query_count_is_constant(client, posts, other_user, django_assert_num_queries):
    for i in range(10):
        Comment.objects.create(post=posts[0], author=other_user, body=f"c{i}")
    # post lookup + comment page with authors joined
    with django_assert_num_queries(2):
        client.get(f"{POSTS}/{posts[0].id}/comments", {"limit": 10})


@pytest.mark.parametrize("cursor", ["\\" * 600, "not base64!", "x" * 513])
def test_garbage_cursors_are_rejected_not_treated_as_first_page(client, cursor):
    """Found by Schemathesis: DRF skipped invalid base64 characters and served page 1."""
    response = client.get(POSTS, {"cursor": cursor})
    assert response.status_code == 422
