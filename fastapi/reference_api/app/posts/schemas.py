from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator
from pydantic_core import PydanticCustomError

from app.core.types import PythonStrip, SafeChars

Strict = ConfigDict(extra="forbid")
Title = Annotated[str, StringConstraints(min_length=1, max_length=200), PythonStrip, SafeChars]
Body = Annotated[str, StringConstraints(max_length=20000), SafeChars]
CommentBody = Annotated[
    str, StringConstraints(min_length=1, max_length=2000), PythonStrip, SafeChars
]
Status = Literal["draft", "published"]


class PostCreate(BaseModel):
    model_config = Strict

    title: Title
    body: Body = ""
    status: Status = "draft"


class PostUpdate(BaseModel):
    """Every field optional, but an explicit `null` is rejected (as DRF does):
    'not sent' means unchanged; `null` is not a valid title."""

    model_config = Strict

    title: Title | None = None
    body: Body | None = None
    status: Status | None = None

    @field_validator("title", "body", "status", mode="before")
    @classmethod
    def reject_null(cls, value: Any) -> Any:
        if value is None:
            raise PydanticCustomError("null", "This field may not be null.")
        return value


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str


class PostOut(BaseModel):
    id: UUID
    title: str
    body: str
    status: Status
    author: AuthorOut
    comment_count: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class PostPage(BaseModel):
    items: list[PostOut]
    next_cursor: str | None


class CommentCreate(BaseModel):
    model_config = Strict

    body: CommentBody


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    body: str
    author: AuthorOut
    created_at: datetime


class CommentPage(BaseModel):
    items: list[CommentOut]
    next_cursor: str | None
