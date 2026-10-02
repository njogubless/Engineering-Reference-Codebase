"""One error model for the whole API: RFC 9457 Problem Details.

Every error response — DRF exceptions, Django exceptions, application errors
and unexpected crashes — leaves the API in the same shape (see
contracts/openapi.yaml `Problem` and docs/architecture.md §4.2).

Where errors come from, and how they are mapped:

- Serializers / DRF (`serializers.ValidationError`)         -> validation_error (422)
- Services, Django-native (`django.core.exceptions.ValidationError`)
                                                            -> validation_error (422)
- Services, application errors (`ConflictError("...")`)     -> conflict (409)
- Anything unexpected (`KeyError`)                          -> internal_error (500)

Services raise Django's own exceptions (or the `AppError` subclasses below),
not DRF exceptions, so business logic does not depend on the HTTP framework.
"""

import logging
import math
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404, HttpRequest, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.settings import api_settings

from apps.core.request_context import get_request_id

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE = "https://errors.reference.dev/"

TITLES = {
    "bad_request": "Bad request",
    "validation_error": "Validation failed",
    "authentication_error": "Authentication required",
    "authorization_error": "Permission denied",
    "not_found": "Not found",
    "method_not_allowed": "Method not allowed",
    "not_acceptable": "Not acceptable",
    "conflict": "Conflict",
    "idempotency_key_reused": "Idempotency key reused",
    "unsupported_media_type": "Unsupported media type",
    "rate_limited": "Too many requests",
    "internal_error": "Internal server error",
    "external_service_error": "External service error",
}


@dataclass(frozen=True)
class FieldError:
    field: str | None
    code: str
    message: str


class AppError(Exception):
    """An error raised deliberately by application code.

    Only for cases Django/DRF have no exception for. Subclass it once per
    error *code*, not once per situation — the message carries the situation.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail


class ConflictError(AppError):
    """The request conflicts with current state (stale version, duplicate, ...)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ExternalServiceError(AppError):
    """A provider we depend on failed. Its raw error is logged, never returned."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "external_service_error"


def problem(
    *,
    status_code: int,
    code: str,
    detail: str | None = None,
    instance: str | None = None,
    errors: list[FieldError] | None = None,
    **extensions: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": PROBLEM_TYPE_BASE + code.replace("_", "-"),
        "title": TITLES[code],
        "status": status_code,
        "code": code,
        "request_id": get_request_id() or "-",
    }
    if detail:
        body["detail"] = detail
    if instance:
        body["instance"] = instance
    if errors:
        body["errors"] = [{"field": e.field, "code": e.code, "message": e.message} for e in errors]
    body.update(extensions)
    return body


def flatten_validation_errors(detail: Any, path: str | None = None) -> list[FieldError]:
    """Turn DRF's nested error structure into a flat list with dotted paths.

    {"items": [{}, {"name": ["required"]}]}  ->  [FieldError("items.1.name", ...)]
    {"non_field_errors": ["..."]}            ->  [FieldError(None, ...)]
    """
    if isinstance(detail, dict):
        result: list[FieldError] = []
        for key, value in detail.items():
            is_general = key == api_settings.NON_FIELD_ERRORS_KEY
            child = path if is_general else _join(path, str(key))
            result.extend(flatten_validation_errors(value, child))
        return result
    if isinstance(detail, list):
        if all(isinstance(item, str) for item in detail):  # ErrorDetail is a str
            return [_field_error(path, item) for item in detail]
        result = []
        for index, item in enumerate(detail):
            result.extend(flatten_validation_errors(item, _join(path, str(index))))
        return result
    return [_field_error(path, detail)]


def _join(path: str | None, key: str) -> str:
    return f"{path}.{key}" if path else key


def _field_error(path: str | None, item: Any) -> FieldError:
    return FieldError(field=path, code=str(getattr(item, "code", "invalid")), message=str(item))


# DRF exception class -> our error code. Checked in order (subclasses first).
_DRF_CODES: list[tuple[type[exceptions.APIException], str]] = [
    (exceptions.ValidationError, "validation_error"),
    (exceptions.ParseError, "bad_request"),
    (exceptions.NotAuthenticated, "authentication_error"),
    (exceptions.AuthenticationFailed, "authentication_error"),
    (exceptions.PermissionDenied, "authorization_error"),
    (exceptions.NotFound, "not_found"),
    (exceptions.MethodNotAllowed, "method_not_allowed"),
    (exceptions.NotAcceptable, "not_acceptable"),
    (exceptions.UnsupportedMediaType, "unsupported_media_type"),
    (exceptions.Throttled, "rate_limited"),
]


def _to_drf_exception(exc: Exception) -> Exception:
    """Translate Django-native exceptions raised by services into DRF ones."""
    if isinstance(exc, DjangoValidationError):
        return exceptions.ValidationError(as_serializer_error(exc))
    if isinstance(exc, Http404 | ObjectDoesNotExist):
        return exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        return exceptions.PermissionDenied()
    return exc


def problem_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """DRF `EXCEPTION_HANDLER`: every exception raised in an API view ends here."""
    request = context.get("request")
    instance = request.path if request is not None else None
    exc = _to_drf_exception(exc)

    if isinstance(exc, AppError):
        if exc.status_code >= 500:
            logger.error("app_error", extra={"code": exc.code}, exc_info=exc)
        body = problem(
            status_code=exc.status_code, code=exc.code, detail=exc.detail, instance=instance
        )
        return Response(body, status=exc.status_code, content_type=PROBLEM_CONTENT_TYPE)

    if isinstance(exc, exceptions.APIException):
        return _api_exception_response(exc, instance)

    # Unexpected: log everything, return nothing internal. The request_id in
    # the body is how the client's report gets matched to this log line.
    logger.error("unhandled_exception", exc_info=exc)
    body = problem(
        status_code=500,
        code="internal_error",
        detail="An unexpected error occurred.",
        instance=instance,
    )
    return Response(body, status=500, content_type=PROBLEM_CONTENT_TYPE)


def _api_exception_response(exc: exceptions.APIException, instance: str | None) -> Response:
    code = next(
        (code for cls, code in _DRF_CODES if isinstance(exc, cls)),
        "bad_request" if exc.status_code < 500 else "internal_error",
    )
    status_code = exc.status_code
    headers: dict[str, str] = {}
    extensions: dict[str, Any] = {}
    errors: list[FieldError] | None = None
    detail: str | None

    if isinstance(exc, exceptions.ValidationError):
        # DRF uses 400 for validation; the contract uses 422 (well-formed but invalid).
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = flatten_validation_errors(exc.detail)
        detail = "One or more fields are invalid."
    else:
        detail = str(exc.detail)

    # `wait` is set by DRF at runtime but missing from its type stubs.
    wait: float | None = getattr(exc, "wait", None)
    if isinstance(exc, exceptions.Throttled) and wait is not None:
        # Round up: retrying a fraction of a second early would just be throttled again.
        retry_after = max(0, math.ceil(wait))
        headers["Retry-After"] = str(retry_after)
        extensions["retry_after"] = retry_after

    auth_header = getattr(exc, "auth_header", None)
    if auth_header:
        headers["WWW-Authenticate"] = auth_header

    body = problem(
        status_code=status_code,
        code=code,
        detail=detail,
        instance=instance,
        errors=errors,
        **extensions,
    )
    return Response(body, status=status_code, headers=headers, content_type=PROBLEM_CONTENT_TYPE)


# --- Django-level handlers --------------------------------------------------
# DRF's handler only covers DRF views. These cover everything else (unknown
# URLs, crashes outside DRF) so clients never receive Django's HTML error pages.
# Django uses them only when DEBUG is False.


def _problem_response(
    request: HttpRequest, status_code: int, code: str, detail: str
) -> JsonResponse:
    body = problem(status_code=status_code, code=code, detail=detail, instance=request.path)
    return JsonResponse(body, status=status_code, content_type=PROBLEM_CONTENT_TYPE)


def handler400(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _problem_response(request, 400, "bad_request", "The request could not be processed.")


def handler403(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _problem_response(request, 403, "authorization_error", "Permission denied.")


def handler404(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return _problem_response(request, 404, "not_found", "No resource exists at this path.")


def handler500(request: HttpRequest) -> JsonResponse:
    # Django has already logged the exception via the `django.request` logger.
    return _problem_response(request, 500, "internal_error", "An unexpected error occurred.")
