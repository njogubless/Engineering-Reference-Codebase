"""Request context middleware (pure ASGI).

Pure ASGI rather than Starlette's `BaseHTTPMiddleware`: it adds no extra task
or response buffering, and works with streaming responses.

Responsibilities, in one place because they share the request's lifetime:
1. Accept or generate `X-Request-ID`, expose it via a ContextVar, echo it back.
2. Log one `request_completed` line per request (method, path, status, duration).
3. Turn *unexpected* exceptions into a Problem Details 500 while the request ID
   is still known (see app/core/errors.py for why this is not an exception handler).
"""

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import problem_response
from app.core.request_context import REQUEST_ID_HEADER, request_id_var, resolve_request_id

logger = logging.getLogger("app.request")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        incoming = headers.get(REQUEST_ID_HEADER.lower().encode(), b"").decode("latin-1")
        request_id = resolve_request_id(incoming)
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                message.setdefault("headers", [])
                message["headers"] = [
                    *message["headers"],
                    (REQUEST_ID_HEADER.lower().encode(), request_id.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            if response_started:
                # Too late to send an error body; let the server close the connection.
                logger.error("unhandled_exception_after_response_started", exc_info=exc)
                raise
            logger.error("unhandled_exception", exc_info=exc)
            response = problem_response(
                status_code=500,
                code="internal_error",
                detail="An unexpected error occurred.",
                instance=scope["path"],
            )
            await response(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request_completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)
