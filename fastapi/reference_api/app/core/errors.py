"""One error model for the whole API: RFC 9457 Problem Details.

The FastAPI counterpart of django/reference_api/apps/core/errors.py. Same
contract (contracts/openapi.yaml `Problem`), different mechanics:

- Django/DRF funnel everything through one EXCEPTION_HANDLER function.
- FastAPI registers one handler per exception type with `app.add_exception_handler`.
- Unexpected exceptions are *not* handled with `add_exception_handler(Exception)`:
  Starlette runs that handler outside all user middleware, so the request ID
  would already be gone. `RequestContextMiddleware` handles them instead.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import get_request_id

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

_STATUS_CODES = {
    400: "bad_request",
    401: "authentication_error",
    403: "authorization_error",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    409: "conflict",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
}

# Pydantic error types -> the validator codes Django uses, so clients see the
# same `errors[].code` whichever backend they talk to. Unlisted types pass through.
_PYDANTIC_CODES = {
    "missing": "required",
    "string_too_long": "max_length",
    "too_long": "max_length",
    "string_too_short": "min_length",
    "too_short": "min_length",
    "greater_than": "min_value",
    "greater_than_equal": "min_value",
    "less_than": "max_value",
    "less_than_equal": "max_value",
}


@dataclass(frozen=True)
class FieldError:
    field: str | None
    code: str
    message: str


class AppError(Exception):
    """An error raised deliberately by application code (services).

    Subclass once per error *code*; the message carries the situation.
    """

    status_code = 500
    code = "internal_error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "authorization_error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ExternalServiceError(AppError):
    """A provider we depend on failed. Its raw error is logged, never returned."""

    status_code = 502
    code = "external_service_error"


def problem(
    *,
    status_code: int,
    code: str,
    detail: str | None = None,
    instance: str | None = None,
    errors: Sequence[FieldError] = (),
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


def problem_response(
    *,
    status_code: int,
    code: str,
    detail: str | None = None,
    instance: str | None = None,
    errors: Sequence[FieldError] = (),
    headers: dict[str, str] | None = None,
    **extensions: Any,
) -> JSONResponse:
    body = problem(
        status_code=status_code,
        code=code,
        detail=detail,
        instance=instance,
        errors=errors,
        **extensions,
    )
    return JSONResponse(
        body, status_code=status_code, headers=headers, media_type=PROBLEM_CONTENT_TYPE
    )


def field_errors_from_pydantic(errors: Sequence[Any]) -> list[FieldError]:
    """("body", "items", 1, "name") -> "items.1.name". The location prefix
    (body/query/path/header) is dropped: clients map errors to form fields."""
    result = []
    for error in errors:
        location = [str(part) for part in error.get("loc", ())[1:]]
        result.append(
            FieldError(
                field=".".join(location) or None,
                code=_PYDANTIC_CODES.get(error.get("type", ""), error.get("type", "invalid")),
                message=str(error.get("msg", "Invalid value.")),
            )
        )
    return result


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - narrowing for the type checker
    if exc.status_code >= 500:
        logger.error("app_error", extra={"code": exc.code}, exc_info=exc)
    return problem_response(
        status_code=exc.status_code, code=exc.code, detail=exc.detail, instance=request.url.path
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = exc.errors()
    # FastAPI does not check Content-Type: a form-encoded body sent to a JSON
    # endpoint surfaces as a confusing validation error. Report it as 415, as DRF does.
    content_type = request.headers.get("content-type", "")
    body_errors = any(error.get("loc", ())[:1] == ("body",) for error in errors)
    if body_errors and content_type and not _is_json(content_type):
        return problem_response(
            status_code=415,
            code="unsupported_media_type",
            detail=f"Unsupported media type {content_type.split(';')[0]!r}; send application/json.",
            instance=request.url.path,
        )
    # Unparseable JSON is a malformed request (400), not invalid data (422).
    if any(error.get("type") == "json_invalid" for error in errors):
        return problem_response(
            status_code=400,
            code="bad_request",
            detail="The request body is not valid JSON.",
            instance=request.url.path,
        )
    return problem_response(
        status_code=422,
        code="validation_error",
        detail="One or more fields are invalid.",
        instance=request.url.path,
        errors=field_errors_from_pydantic(errors),
    )


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = _STATUS_CODES.get(
        exc.status_code, "bad_request" if exc.status_code < 500 else "internal_error"
    )
    headers = dict(exc.headers or {})
    extensions: dict[str, Any] = {}
    if exc.status_code == 429 and "Retry-After" in headers:
        extensions["retry_after"] = int(headers["Retry-After"])
    detail = exc.detail if isinstance(exc.detail, str) else None
    return problem_response(
        status_code=exc.status_code,
        code=code,
        detail=detail,
        instance=request.url.path,
        headers=headers,
        **extensions,
    )


def _is_json(content_type: str) -> bool:
    media_type = content_type.split(";")[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    # Starlette's HTTPException covers FastAPI's subclass and router-level 404/405.
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
