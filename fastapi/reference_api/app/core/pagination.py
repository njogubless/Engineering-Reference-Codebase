"""Keyset (cursor) pagination, written out by hand.

The Django reference uses DRF's CursorPagination; this is the underlying
technique. To fetch the page after row (t, id) in newest-first order:

    WHERE (created_at, id) < (t, id)
    ORDER BY created_at DESC, id DESC
    LIMIT limit + 1          -- one extra row tells us whether a next page exists

The row comparison uses the (created_at, id) index directly, so page 1000
costs the same as page 1 — unlike OFFSET, which reads and discards every
skipped row. The cursor is opaque to clients (base64 JSON); they must not
build or parse it, which leaves the server free to change it.
"""

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query

from app.core.errors import ValidationFailedError

MAX_LIMIT = 100


@dataclass(frozen=True)
class Position:
    created_at: datetime
    id: UUID


def encode_cursor(position: Position) -> str:
    raw = json.dumps({"t": position.created_at.isoformat(), "i": str(position.id)})
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> Position:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        position = Position(created_at=datetime.fromisoformat(data["t"]), id=UUID(data["i"]))
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeError):
        raise ValidationFailedError.field("cursor", "invalid", "Invalid cursor.") from None
    if position.created_at.tzinfo is None:
        raise ValidationFailedError.field("cursor", "invalid", "Invalid cursor.")
    return position


@dataclass(frozen=True)
class PageParams:
    position: Position | None
    limit: int


def page_params(
    cursor: Annotated[
        str | None, Query(max_length=512, description="Opaque cursor from `next_cursor`.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Page size (1-100).")] = 20,
) -> PageParams:
    return PageParams(position=decode_cursor(cursor) if cursor else None, limit=limit)


PageDep = Annotated[PageParams, Depends(page_params)]
