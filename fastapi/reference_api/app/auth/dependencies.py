"""Authentication as FastAPI dependencies.

    CurrentUser   -> 401 unless a valid access token is sent
    OptionalUser  -> None for anonymous requests; still 401 for an *invalid* token

An invalid token is never silently treated as anonymous: a client with a
broken token should find out, not quietly see less data.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import User
from app.auth.security import decode_access_token
from app.core.config import Settings, get_settings
from app.core.db import SessionDep
from app.core.errors import AuthenticationError

_bearer = HTTPBearer(auto_error=False, description="Access token from POST /api/v1/auth/token")

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def optional_user(
    credentials: Credentials, session: SessionDep, settings: SettingsDep
) -> User | None:
    if credentials is None:
        return None
    user = await session.get(User, decode_access_token(credentials.credentials, settings))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


async def current_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise AuthenticationError("Authentication credentials were not provided.")
    return user


OptionalUser = Annotated[User | None, Depends(optional_user)]
CurrentUser = Annotated[User, Depends(current_user)]
