from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAuthorOrReadOnly(BasePermission):
    """Object-level rule: anyone who can see an object may read it; only its
    author may change it. Phase 4 extends this with roles (RBAC)."""

    message = "Only the author can change this."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return request.method in SAFE_METHODS or obj.author_id == request.user.pk
