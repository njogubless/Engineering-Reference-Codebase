"""Cursor pagination in the contract's shape: `{"items": [...], "next_cursor": ...}`.

Built on DRF's CursorPagination rather than hand-written: DRF already handles
opaque cursor encoding and ties between equal timestamps. What is customised:

- the response shape (the contract's `CursorPage`, not DRF's next/previous URLs);
- `limit` outside 1-100 is a 422, not silently clamped — a client asking for
  500 items should learn it gets at most 100;
- a malformed cursor is a 422 on the `cursor` field (DRF's default is a 404).

Why cursors, not page numbers: with offset pagination, a post created while a
user scrolls shifts every later page by one (duplicates or skipped items), and
`OFFSET 100000` makes the database walk 100 000 rows. A cursor says "continue
after this row". Phase 6 compares both in depth.
"""

import base64
import binascii
from typing import Any
from urllib.parse import parse_qs, urlparse

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import Cursor, CursorPagination
from rest_framework.request import Request
from rest_framework.response import Response

MAX_LIMIT = 100
MAX_CURSOR_LENGTH = 512


class NewestFirstCursorPagination(CursorPagination):
    page_size = 20
    max_page_size = MAX_LIMIT
    page_size_query_param = "limit"
    # A unique tiebreaker makes the order total, so pages are stable.
    ordering = ("-created_at", "-id")

    def get_page_size(self, request: Request) -> int:
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None:
            return self.page_size
        try:
            limit = int(raw)
        except ValueError:
            raise ValidationError({"limit": ["A valid integer is required."]}) from None
        if not 1 <= limit <= MAX_LIMIT:
            raise ValidationError({"limit": [f"Must be between 1 and {MAX_LIMIT}."]})
        return limit

    def decode_cursor(self, request: Request) -> Cursor | None:
        raw = request.query_params.get(self.cursor_query_param)
        # DRF decodes leniently: invalid base64 characters are skipped, so
        # garbage silently becomes "first page". Validate strictly instead.
        if raw is not None:
            try:
                if len(raw) > MAX_CURSOR_LENGTH:
                    raise ValueError("too long")
                base64.b64decode(raw.encode("ascii"), validate=True)
            except (ValueError, binascii.Error):
                raise ValidationError({"cursor": ["Invalid cursor."]}) from None
        try:
            return super().decode_cursor(request)
        except NotFound:
            raise ValidationError({"cursor": ["Invalid cursor."]}) from None

    def get_paginated_response(self, data: Any) -> Response:
        return Response({"items": data, "next_cursor": _cursor_from_link(self.get_next_link())})

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["items", "next_cursor"],
            "properties": {
                "items": schema,
                "next_cursor": {"type": "string", "nullable": True},
            },
        }


class OldestFirstCursorPagination(NewestFirstCursorPagination):
    ordering = ("created_at", "id")


def _cursor_from_link(link: str | None) -> str | None:
    if link is None:
        return None
    return parse_qs(urlparse(link).query).get("cursor", [None])[0]
