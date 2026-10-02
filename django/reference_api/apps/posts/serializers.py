from rest_framework import serializers

from apps.accounts.models import User
from apps.core.serializers import StrictInputMixin
from apps.posts.models import Comment, Post


class AuthorSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("id", "display_name")
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer[Post]):
    """Output. Expects `comment_count` annotated by the selectors."""

    author = AuthorSerializer(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "body",
            "status",
            "author",
            "comment_count",
            "created_at",
            "updated_at",
            "published_at",
        )
        read_only_fields = fields


class PostWriteSerializer(StrictInputMixin, serializers.Serializer):  # type: ignore[type-arg]
    """Input for create (title required) and partial update (any subset)."""

    title = serializers.CharField(min_length=1, max_length=200)
    body = serializers.CharField(
        max_length=20000, allow_blank=True, trim_whitespace=False, required=False
    )
    status = serializers.ChoiceField(choices=Post.Status.choices, required=False)


class CommentSerializer(serializers.ModelSerializer[Comment]):
    author = AuthorSerializer(read_only=True)
    post_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "post_id", "body", "author", "created_at")
        read_only_fields = fields


class CommentWriteSerializer(StrictInputMixin, serializers.Serializer):  # type: ignore[type-arg]
    body = serializers.CharField(min_length=1, max_length=2000)
