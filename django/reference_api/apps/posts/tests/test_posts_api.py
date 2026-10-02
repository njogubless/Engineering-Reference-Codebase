import pytest
from django.db import IntegrityError

from apps.posts.models import Comment, Post

pytestmark = pytest.mark.django_db

POSTS = "/api/v1/posts"


def detail(post) -> str:
    return f"{POSTS}/{post.id}"


class TestCreate:
    def test_author_is_the_authenticated_user(self, client_as, user):
        response = client_as(user).post(
            POSTS, {"title": "  Hello  ", "body": "World"}, format="json"
        )
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Hello"
        assert body["author"] == {"id": str(user.id), "display_name": "Ada"}
        assert body["status"] == "draft"
        assert body["published_at"] is None
        assert body["comment_count"] == 0

    def test_an_author_in_the_body_is_rejected_not_ignored(self, client_as, user, other_user):
        response = client_as(user).post(
            POSTS, {"title": "x", "author": str(other_user.id)}, format="json"
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "unknown_field"

    def test_publishing_on_create_sets_published_at(self, client_as, user):
        response = client_as(user).post(POSTS, {"title": "x", "status": "published"}, format="json")
        assert response.json()["published_at"] is not None

    def test_requires_authentication(self, client):
        assert client.post(POSTS, {"title": "x"}, format="json").status_code == 401

    @pytest.mark.parametrize(
        ("payload", "field", "code"),
        [
            ({}, "title", "required"),
            ({"title": ""}, "title", "blank"),
            ({"title": "x" * 201}, "title", "max_length"),
            ({"title": "x", "status": "archived"}, "status", "invalid_choice"),
        ],
    )
    def test_validation(self, client_as, user, payload, field, code):
        response = client_as(user).post(POSTS, payload, format="json")
        assert response.status_code == 422
        assert (field, code) in {(e["field"], e["code"]) for e in response.json()["errors"]}


class TestVisibility:
    def test_anyone_can_read_a_published_post(self, client, make_post):
        assert client.get(detail(make_post())).status_code == 200

    def test_drafts_are_visible_to_their_author(self, client_as, user, make_post):
        assert client_as(user).get(detail(make_post(status="draft"))).status_code == 200

    def test_other_users_drafts_are_404_not_403(self, client, client_as, other_user, make_post):
        draft = make_post(status="draft")
        assert client.get(detail(draft)).status_code == 404
        assert client_as(other_user).get(detail(draft)).status_code == 404

    def test_list_contains_only_published_posts(self, client, make_post):
        published = make_post(title="visible")
        make_post(title="hidden", status="draft")
        items = client.get(POSTS).json()["items"]
        assert [item["id"] for item in items] == [str(published.id)]


class TestUpdateAndDelete:
    def test_author_can_update_and_publish(self, client_as, user, make_post):
        post = make_post(status="draft")
        response = client_as(user).patch(detail(post), {"status": "published"}, format="json")
        assert response.status_code == 200
        assert response.json()["published_at"] is not None

    def test_unpublishing_clears_published_at(self, client_as, user, make_post):
        response = client_as(user).patch(detail(make_post()), {"status": "draft"}, format="json")
        assert response.json()["published_at"] is None

    def test_other_users_get_403_on_a_post_they_can_see(self, client_as, other_user, make_post):
        post = make_post()
        api = client_as(other_user)
        assert api.patch(detail(post), {"title": "hijacked"}, format="json").status_code == 403
        assert api.delete(detail(post)).status_code == 403
        post.refresh_from_db()
        assert post.title == "A title"

    def test_empty_patch_is_rejected(self, client_as, user, make_post):
        response = client_as(user).patch(detail(make_post()), {}, format="json")
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "empty_update"

    def test_delete_removes_comments(self, client_as, user, other_user, make_post):
        post = make_post()
        Comment.objects.create(post=post, author=other_user, body="hi")
        assert client_as(user).delete(detail(post)).status_code == 204
        assert not Comment.objects.exists()


class TestComments:
    def test_create_and_list_oldest_first(self, client_as, client, user, other_user, make_post):
        post = make_post()
        for text in ("first", "second"):
            response = client_as(other_user).post(
                f"{detail(post)}/comments", {"body": text}, format="json"
            )
            assert response.status_code == 201
        items = client.get(f"{detail(post)}/comments").json()["items"]
        assert [c["body"] for c in items] == ["first", "second"]
        assert items[0]["author"]["display_name"] == "Grace"
        assert client.get(detail(post)).json()["comment_count"] == 2

    def test_own_draft_cannot_be_commented_on(self, client_as, user, make_post):
        response = client_as(user).post(
            f"{detail(make_post(status='draft'))}/comments", {"body": "x"}, format="json"
        )
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "post_not_published"

    def test_only_the_comment_author_can_delete_it(self, client_as, user, other_user, make_post):
        post = make_post()
        comment = Comment.objects.create(post=post, author=other_user, body="hi")
        url = f"{detail(post)}/comments/{comment.id}"
        assert client_as(user).delete(url).status_code == 403
        assert client_as(other_user).delete(url).status_code == 204

    def test_comment_must_belong_to_the_post_in_the_path(self, client_as, other_user, make_post):
        comment = Comment.objects.create(post=make_post(), author=other_user, body="hi")
        url = f"{detail(make_post())}/comments/{comment.id}"
        assert client_as(other_user).delete(url).status_code == 404


class TestDatabaseConstraints:
    """The database enforces the rules even when code bypasses the services."""

    def test_published_without_date_is_impossible(self, user):
        with pytest.raises(IntegrityError):
            Post.objects.create(author=user, title="x", status="published", published_at=None)

    def test_blank_title_is_impossible(self, user):
        with pytest.raises(IntegrityError):
            Post.objects.create(author=user, title="")
