from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from app.core.types import NonBlank, PythonStrip, SafeChars

Strict = ConfigDict(extra="forbid")  # unknown fields are 422 unknown_field, as in the Django API


class RegisterRequest(BaseModel):
    model_config = Strict

    email: Annotated[EmailStr, StringConstraints(max_length=254)]
    password: Annotated[str, StringConstraints(min_length=10, max_length=128), SafeChars]
    display_name: Annotated[
        str, StringConstraints(min_length=1, max_length=100), PythonStrip, SafeChars
    ]


class TokenRequest(BaseModel):
    model_config = Strict

    email: Annotated[str, StringConstraints(min_length=1, max_length=254), SafeChars, NonBlank]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128), SafeChars]


class RefreshRequest(BaseModel):
    model_config = Strict

    refresh: Annotated[str, StringConstraints(min_length=1, max_length=1024), SafeChars, NonBlank]


class TokenPair(BaseModel):
    access: str
    refresh: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    date_joined: datetime
