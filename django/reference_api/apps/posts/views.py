"""HTTP layer only: parse input, call a selector or service, serialize output.

Visibility vs permission:
- Can the requester *see* the post? No -> 404 (selectors.get_visible_post).
- Can they *change* it? No -> 403 (IsAuthorOrReadOnly).
"""

from typing import Any
from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.request import require_user
from apps.core.pagination import NewestFirstCursorPagination, OldestFirstCursorPagination
from apps.posts import selectors, services
from apps.posts.models import Comment, Post
from apps.posts.permissions import IsAuthorOrReadOnly
from apps.posts.serializers import (
    CommentSerializer,
    CommentWriteSerializer,
    PostSerializer,
    PostWriteSerializer,
)


class PostListCreateView(GenericAPIView[Post]):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = NewestFirstCursorPagination
    serializer_class = PostSerializer

    def get_queryset(self) -> Any:
        return selectors.published_posts()

    @extend_schema(operation_id="listPosts")
    def get(self, request: Request) -> Response:
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(PostSerializer(page, many=True).data)

    @extend_schema(
        operation_id="createPost", request=PostWriteSerializer, responses={201: PostSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = PostWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = services.create_post(author=require_user(request), **serializer.validated_data)
        # Re-read through the selector so the response has the same shape
        # (author, comment_count) as every other read.
        created = selectors.get_visible_post(post.id, request.user)
        return Response(PostSerializer(created).data, status=status.HTTP_201_CREATED)


class PostDetailView(GenericAPIView[Post]):
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    serializer_class = PostSerializer

    def get_post(self, post_id: UUID) -> Post:
        post = selectors.get_visible_post(post_id, self.request.user)
        self.check_object_permissions(self.request, post)
        return post

    @extend_schema(operation_id="getPost")
    def get(self, request: Request, post_id: UUID) -> Response:
        return Response(PostSerializer(self.get_post(post_id)).data)

    @extend_schema(operation_id="updatePost", request=PostWriteSerializer, responses=PostSerializer)
    def patch(self, request: Request, post_id: UUID) -> Response:
        post = self.get_post(post_id)
        serializer = PostWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_post(post=post, changes=serializer.validated_data)
        return Response(PostSerializer(selectors.get_visible_post(post.id, request.user)).data)

    @extend_schema(operation_id="deletePost", responses={204: None})
    def delete(self, request: Request, post_id: UUID) -> Response:
        services.delete_post(post=self.get_post(post_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentListCreateView(GenericAPIView[Comment]):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = OldestFirstCursorPagination
    serializer_class = CommentSerializer

    @extend_schema(operation_id="listComments")
    def get(self, request: Request, post_id: UUID) -> Response:
        post = selectors.get_visible_post(post_id, request.user)
        page = self.paginate_queryset(selectors.post_comments(post))
        return self.get_paginated_response(CommentSerializer(page, many=True).data)

    @extend_schema(
        operation_id="createComment",
        request=CommentWriteSerializer,
        responses={201: CommentSerializer},
    )
    def post(self, request: Request, post_id: UUID) -> Response:
        post = selectors.get_visible_post(post_id, request.user)
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.create_comment(
            post=post, author=require_user(request), **serializer.validated_data
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class CommentDetailView(GenericAPIView[Comment]):
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    serializer_class = CommentSerializer

    @extend_schema(operation_id="deleteComment", responses={204: None})
    def delete(self, request: Request, post_id: UUID, comment_id: UUID) -> Response:
        post = selectors.get_visible_post(post_id, request.user)
        comment = selectors.get_comment(post, comment_id)
        self.check_object_permissions(request, comment)
        services.delete_comment(comment=comment)
        return Response(status=status.HTTP_204_NO_CONTENT)
