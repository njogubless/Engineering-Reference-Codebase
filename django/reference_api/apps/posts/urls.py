from django.urls import path

from apps.posts import views

urlpatterns = [
    path("posts", views.PostListCreateView.as_view(), name="post-list"),
    path("posts/<uuid:post_id>", views.PostDetailView.as_view(), name="post-detail"),
    path(
        "posts/<uuid:post_id>/comments", views.CommentListCreateView.as_view(), name="comment-list"
    ),
    path(
        "posts/<uuid:post_id>/comments/<uuid:comment_id>",
        views.CommentDetailView.as_view(),
        name="comment-detail",
    ),
]
