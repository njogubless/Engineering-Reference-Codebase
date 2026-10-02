"""Views that raise each kind of error, used only by test_errors.py."""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import path
from rest_framework import exceptions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.errors import ConflictError, ExternalServiceError
from apps.core.views import PublicAPIView
from config.urls import (  # noqa: F401 - Django looks these up on the active URLconf
    handler400,
    handler403,
    handler404,
    handler500,
)
from config.urls import urlpatterns as project_urlpatterns


class ItemSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(max_length=5)


class OrderSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField()
    items = ItemSerializer(many=True)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("title") == "forbidden":
            raise serializers.ValidationError("This title is not allowed.")
        return attrs


def raising(exc: Exception) -> type[PublicAPIView]:
    class RaisingView(PublicAPIView):
        def get(self, request: Request) -> Response:
            raise exc

    return RaisingView


class ValidateView(PublicAPIView):
    def post(self, request: Request) -> Response:
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class DefaultPermissionView(APIView):
    """No explicit permission_classes: inherits the project default."""

    def get(self, request: Request) -> Response:
        return Response({"secret": "data"})


urlpatterns = [
    *project_urlpatterns,
    path("t/validate", ValidateView.as_view()),
    path(
        "t/django-validation",
        raising(DjangoValidationError({"email": ["Already used."]})).as_view(),
    ),
    path("t/django-permission", raising(DjangoPermissionDenied()).as_view()),
    path("t/drf-not-found", raising(exceptions.NotFound()).as_view()),
    path("t/throttled", raising(exceptions.Throttled(wait=12.4)).as_view()),
    path("t/conflict", raising(ConflictError("Version 3 is stale.")).as_view()),
    path("t/external", raising(ExternalServiceError("Payment provider unavailable.")).as_view()),
    path("t/default-permission", DefaultPermissionView.as_view()),
    path("t/crash", raising(KeyError("secret-internal-detail")).as_view()),
]
