import logging
from collections.abc import Callable

import redis
from django.conf import settings
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.features import public_flags

logger = logging.getLogger(__name__)

READINESS_TIMEOUT_SECONDS = 2


def check_database() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def check_redis() -> None:
    client = redis.Redis.from_url(
        settings.REDIS_URL,
        socket_timeout=READINESS_TIMEOUT_SECONDS,
        socket_connect_timeout=READINESS_TIMEOUT_SECONDS,
    )
    try:
        client.ping()
    finally:
        client.close()


# Only dependencies without which this process cannot serve requests belong here.
# An optional dependency (e.g. an email provider) failing must not take the
# instance out of the load balancer.
READINESS_CHECKS: dict[str, Callable[[], None]] = {
    "database": check_database,
    "redis": check_redis,
}


class PublicAPIView(APIView):
    """Endpoints that are intentionally reachable without credentials."""

    authentication_classes = ()
    permission_classes = (AllowAny,)


class LivenessView(PublicAPIView):
    """Is the process alive? Never checks dependencies: if the database is down,
    restarting every API process would not fix it and would add load."""

    @extend_schema(
        operation_id="getLiveness",
        responses=inline_serializer("Liveness", {"status": serializers.CharField()}),
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(PublicAPIView):
    """Can this instance serve traffic? Load balancers stop routing to it when not."""

    @extend_schema(
        operation_id="getReadiness",
        responses={
            (code, "application/json"): inline_serializer(
                f"Readiness{code}",
                {"status": serializers.CharField(), "checks": serializers.DictField()},
            )
            for code in (200, 503)
        },
    )
    def get(self, request: Request) -> Response:
        checks: dict[str, str] = {}
        for name, check in READINESS_CHECKS.items():
            try:
                check()
                checks[name] = "ok"
            except Exception:
                # Broad catch is deliberate: any failure means "not ready".
                # Details go to logs only — this endpoint is public.
                logger.warning("readiness_check_failed", extra={"check": name}, exc_info=True)
                checks[name] = "fail"
        ready = all(result == "ok" for result in checks.values())
        return Response(
            {"status": "ok" if ready else "unavailable", "checks": checks},
            status=200 if ready else 503,
        )


class MetaView(PublicAPIView):
    @extend_schema(
        operation_id="getMeta",
        responses=inline_serializer(
            "Meta",
            {
                "api_version": serializers.CharField(),
                "environment": serializers.CharField(),
                "features": serializers.DictField(child=serializers.BooleanField()),
            },
        ),
    )
    def get(self, request: Request) -> Response:
        return Response(
            {
                "api_version": "1",
                "environment": settings.ENVIRONMENT,
                "features": public_flags(),
            }
        )
