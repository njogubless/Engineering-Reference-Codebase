from datetime import UTC, datetime, timedelta
from typing import Any

import httpx2
import pytest
from sqlalchemy import event, text

from tests.conftest import signup

POSTS = "/api/v1/posts"


@pytest.fixture
async def ada(api: httpx2.AsyncClient) -> dict[str, str]:
    return await signup(api, "ada@example.com", "Ada")


@pytest.fixture
async def grace(api: httpx2.AsyncClient) -> dict[str, str]:
    return await signup(api, "grace@example.com", "Grace")


async def create(api, headers, **fields) -> dict[str, Any]:
    response = await api.post(POSTS, json={"title": "A title", **fields}, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


class TestCreate:
    async def test_author_is_the_authenticated_user(self, api, ada):
        post = await create(api, ada, title="  Hello  ")
        assert post["title"] == "Hello"
        assert post["author"]["display_name"] == "Ada"
        assert post["status"] == "draft"
        assert post["published_at"] is None
        assert post["comment_count"] == 0
        assert post["created_at"].endswith("Z")  # RFC 3339 UTC on the wire

    async def test_author_in_body_is_rejected(self, api, ada):
        response = await api.post(POSTS, json={"title": "x", "author": "someone"}, headers=ada)
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "unknown_field"

    async def test_requires_authentication(self, api):
        assert (await api.post(POSTS, json={"title": "x"})).status_code == 401

    @pytest.mark.parametrize(
        ("payload", "field", "code"),
        [
            ({}, "title", "required"),
            ({"title": "x" * 201}, "title", "max_length"),
            ({"title": "x", "status": "archived"}, "status", "invalid_choice"),
        ],
    )
    async def test_validation(self, api, ada, payload, field, code):
        response = await api.post(POSTS, json=payload, headers=ada)
        assert response.status_code == 422
        assert (field, code) in {(e["field"], e["code"]) for e in response.json()["errors"]}


class TestVisibilityAndOwnership:
    async def test_other_users_drafts_are_404(self, api, ada, grace):
        draft = await create(api, ada)
        assert (await api.get(f"{POSTS}/{draft['id']}", headers=ada)).status_code == 200
        assert (await api.get(f"{POSTS}/{draft['id']}", headers=grace)).status_code == 404
        assert (await api.get(f"{POSTS}/{draft['id']}")).status_code == 404

    async def test_non_authors_get_403_on_visible_posts(self, api, ada, grace):
        post = await create(api, ada, status="published")
        url = f"{POSTS}/{post['id']}"
        assert (await api.patch(url, json={"title": "hijacked"}, headers=grace)).status_code == 403
        assert (await api.delete(url, headers=grace)).status_code == 403

    async def test_publish_and_unpublish(self, api, ada):
        post = await create(api, ada)
        url = f"{POSTS}/{post['id']}"
        published = (await api.patch(url, json={"status": "published"}, headers=ada)).json()
        assert published["published_at"] is not None
        draft = (await api.patch(url, json={"status": "draft"}, headers=ada)).json()
        assert draft["published_at"] is None

    async def test_empty_patch_and_explicit_null(self, api, ada):
        url = f"{POSTS}/{(await create(api, ada))['id']}"
        empty = await api.patch(url, json={}, headers=ada)
        assert empty.status_code == 422
        assert empty.json()["errors"][0]["code"] == "empty_update"
        null = await api.patch(url, json={"title": None}, headers=ada)
        assert null.json()["errors"][0] == {
            "field": "title",
            "code": "null",
            "message": "This field may not be null.",
        }

    async def test_delete_cascades_to_comments(self, api, ada, grace, app):
        post = await create(api, ada, status="published")
        await api.post(f"{POSTS}/{post['id']}/comments", json={"body": "hi"}, headers=grace)
        assert (await api.delete(f"{POSTS}/{post['id']}", headers=ada)).status_code == 204
        async with app.state.engine.connect() as connection:
            assert (await connection.execute(text("SELECT count(*) FROM comments"))).scalar() == 0


class TestComments:
    async def test_create_list_and_count(self, api, ada, grace):
        post = await create(api, ada, status="published")
        url = f"{POSTS}/{post['id']}/comments"
        for body in ("first", "second"):
            assert (await api.post(url, json={"body": body}, headers=grace)).status_code == 201
        items = (await api.get(url)).json()["items"]
        assert [c["body"] for c in items] == ["first", "second"]
        assert (await api.get(f"{POSTS}/{post['id']}")).json()["comment_count"] == 2

    async def test_drafts_cannot_be_commented_on(self, api, ada):
        draft = await create(api, ada)
        response = await api.post(
            f"{POSTS}/{draft['id']}/comments", json={"body": "x"}, headers=ada
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "post_not_published"

    async def test_only_comment_author_deletes_and_pair_must_match(self, api, ada, grace):
        post = await create(api, ada, status="published")
        other = await create(api, ada, status="published")
        comment = (
            await api.post(f"{POSTS}/{post['id']}/comments", json={"body": "x"}, headers=grace)
        ).json()
        assert (
            await api.delete(f"{POSTS}/{other['id']}/comments/{comment['id']}", headers=grace)
        ).status_code == 404
        assert (
            await api.delete(f"{POSTS}/{post['id']}/comments/{comment['id']}", headers=ada)
        ).status_code == 403
        assert (
            await api.delete(f"{POSTS}/{post['id']}/comments/{comment['id']}", headers=grace)
        ).status_code == 204


class TestPagination:
    @pytest.fixture
    async def many(self, api, ada, app) -> list[str]:
        """12 published posts; five share each timestamp to exercise the tiebreaker."""
        await create(api, ada)  # make sure the author exists
        now = datetime.now(UTC)
        async with app.state.engine.begin() as connection:
            author = (await connection.execute(text("SELECT id FROM users LIMIT 1"))).scalar()
            await connection.execute(text("DELETE FROM posts"))
            for i in range(12):
                at = now - timedelta(minutes=i // 5)
                await connection.execute(
                    text(
                        "INSERT INTO posts (id, author_id, title, body, status,"
                        " published_at, created_at, updated_at)"
                        " VALUES (gen_random_uuid(), :author, :title, '', 'published',"
                        " :at, :at, :at)"
                    ),
                    {"author": author, "title": f"p{i}", "at": at},
                )
            rows = await connection.execute(
                text("SELECT id FROM posts ORDER BY created_at DESC, id DESC")
            )
            return [str(row[0]) for row in rows]

    async def test_walking_pages_returns_every_post_once_in_order(self, api, many):
        seen, cursor = [], None
        while True:
            params = {"limit": 5, **({"cursor": cursor} if cursor else {})}
            page = (await api.get(POSTS, params=params)).json()
            seen += [item["id"] for item in page["items"]]
            if (cursor := page["next_cursor"]) is None:
                break
        assert seen == many

    @pytest.mark.parametrize("limit", ["0", "101", "abc"])
    async def test_invalid_limit_is_422(self, api, limit):
        response = await api.get(POSTS, params={"limit": limit})
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "limit"

    @pytest.mark.parametrize("cursor", ["not-base64!", "eyJ0IjogIngifQ=="])
    async def test_tampered_cursor_is_422(self, api, cursor):
        response = await api.get(POSTS, params={"cursor": cursor})
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "cursor"

    async def test_one_query_per_page_regardless_of_size(self, api, many, app):
        statements: list[str] = []
        listener = lambda *args: statements.append(args[2])  # noqa: E731
        event.listen(app.state.engine.sync_engine, "before_cursor_execute", listener)
        try:
            await api.get(POSTS, params={"limit": 12})
        finally:
            event.remove(app.state.engine.sync_engine, "before_cursor_execute", listener)
        assert len(statements) == 1


@pytest.mark.parametrize("title", ["\f", "   ", "\t\n"])
async def test_whitespace_only_titles_are_422_not_500(api, ada, title):
    """Found by Schemathesis: "\\f" was stripped to "" after the length check,
    and the database CHECK constraint raised a 500."""
    response = await api.post(POSTS, json={"title": title}, headers=ada)
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "title"


@pytest.mark.parametrize("title", ["\x1d", "\x1c\x1f", "\x85"])
async def test_python_whitespace_is_trimmed_like_django(api, ada, title):
    """Found by Schemathesis: Pydantic's strip_whitespace keeps "\\x1d" (Rust's
    notion of whitespace); DRF strips it. Both backends must agree."""
    response = await api.post(POSTS, json={"title": title}, headers=ada)
    assert response.status_code == 422
