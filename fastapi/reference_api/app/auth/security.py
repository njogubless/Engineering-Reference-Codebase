"""Password hashing, access tokens and refresh-token secrets.

The Django reference gets all of this from Django + simplejwt. Doing it by
hand here shows what those libraries do for you.
"""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from functools import lru_cache
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import AuthenticationError, FieldError

ALGORITHM = "HS256"


@lru_cache
def _hasher(time_cost: int, memory_cost: int) -> tuple[PasswordHasher, str]:
    """Argon2id hasher plus a dummy hash made with the same cost.

    The dummy hash is verified when the email does not exist, so a failed
    login takes the same time either way: response timing must not reveal
    which emails have accounts.
    """
    hasher = PasswordHasher(time_cost=time_cost, memory_cost=memory_cost)
    return hasher, hasher.hash("timing-equaliser-not-a-real-password")


def _for(settings: Settings) -> tuple[PasswordHasher, str]:
    return _hasher(settings.argon2_time_cost, settings.argon2_memory_cost_kib)


def hash_password(password: str, settings: Settings) -> str:
    return _for(settings)[0].hash(password)


def verify_password(password: str, password_hash: str | None, settings: Settings) -> bool:
    hasher, dummy = _for(settings)
    try:
        # Hashes record their own parameters, so older hashes still verify.
        return hasher.verify(password_hash or dummy, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_problems(password: str, *, email: str, display_name: str) -> list[FieldError]:
    """A small subset of Django's validators, with the same error codes.

    Real projects should use a strength estimator (e.g. zxcvbn) and a
    breached-password check; this shows where they plug in.
    """
    problems = []
    if len(password) < 10:
        problems.append(
            (
                "password_too_short",
                "This password is too short. It must contain at least 10 characters.",
            )
        )
    if password.isdigit():
        problems.append(("password_entirely_numeric", "This password is entirely numeric."))
    if _too_similar(password, (email, display_name)):
        problems.append(("password_too_similar", "The password is too similar to your details."))
    lowered = password.lower()
    if re.fullmatch(r"(password|qwerty|letmein|welcome)\d*", lowered):
        problems.append(("password_too_common", "This password is too common."))
    return [FieldError(field="password", code=code, message=message) for code, message in problems]


def _too_similar(password: str, attributes: tuple[str, ...], max_similarity: float = 0.7) -> bool:
    """Django's UserAttributeSimilarityValidator algorithm, so both backends
    accept and reject the same passwords: compare against each attribute and
    each word in it, using a similarity ratio rather than a substring test
    (`contract-test-password` is fine for a user named "Contract")."""
    password = password.lower()
    for value in attributes:
        value = value.lower()
        for part in {value, *re.split(r"\W+", value)}:
            if part and SequenceMatcher(a=password, b=part).quick_ratio() >= max_similarity:
                return True
    return False


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
        "jti": secrets.token_hex(16),
        "token_type": "access",
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        # `algorithms` is an allow-list: never let the token choose (alg=none attacks).
        claims = jwt.decode(
            token, settings.secret_key, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]}
        )
        if claims.get("token_type") != "access":
            raise jwt.InvalidTokenError("not an access token")
        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise AuthenticationError("Given token not valid for any token type") from None


def new_refresh_secret() -> tuple[str, str]:
    """(token for the client, hash for the database)."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_secret(token)


def hash_refresh_secret(token: str) -> str:
    # A fast hash is right here (unlike passwords): the token is 384 random
    # bits, so it cannot be brute-forced; the hash only protects a DB leak.
    return hashlib.sha256(token.encode()).hexdigest()
