"""Per-request context shared by middleware, logging and error handling.

A ContextVar (not a thread-local) so it is correct under both WSGI threads
and ASGI tasks.
"""

import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"

# Accept only short, log-safe IDs from clients; anything else is replaced.
# Without this, a client could inject newlines or huge values into every log line.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def resolve_request_id(incoming: str | None) -> str:
    """Return the incoming ID if it is safe to propagate, otherwise a fresh one."""
    if incoming and _VALID_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


def get_request_id() -> str | None:
    return request_id_var.get()
