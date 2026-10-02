"""Structured JSON logging with request context and redaction.

Standard-library `logging` only: a formatter and a filter are all that is
needed, so no structlog/python-json-logger dependency.

Usage — pass context as `extra`, never by formatting it into the message:

    logger.info("order_placed", extra={"order_id": order.id, "total": total})

Messages are stable event names, so logs can be searched and counted.
See docs/patterns/31-logging/README.md for what must never be logged.
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from apps.core.request_context import get_request_id

REDACTED = "[REDACTED]"

# Matched against `extra` keys (case-insensitive, substring). Redaction by key
# is a safety net — the primary rule is to not pass secrets to the logger.
_SENSITIVE_KEY = re.compile(
    r"pass(word)?|secret|token|authorization|cookie|api[_-]?key|session|otp|card|cvv",
    re.IGNORECASE,
)

# Attributes every LogRecord has; anything else came from `extra`.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}


def redact(value: Any) -> Any:
    """Recursively replace values under sensitive keys."""
    if isinstance(value, dict):
        return {
            key: REDACTED if _SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value


class RequestContextFilter(logging.Filter):
    """Adds `request_id` to every record (or "-" outside a request)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        extra = {key: value for key, value in vars(record).items() if key not in _RESERVED}
        payload.update(redact(extra))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # default=str: an unserialisable extra must not crash the log call.
        return json.dumps(payload, default=str)
