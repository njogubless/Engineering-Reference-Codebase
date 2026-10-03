"""Firebase ID-token verification (same rules as the Django API; see
apps/accounts/firebase.py there). firebase-admin is synchronous and may call
the network (Google's keys, revocation), so it runs in a worker thread.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as firebase_auth
from starlette.concurrency import run_in_threadpool

from app.core.errors import AuthenticationError, ExternalServiceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str | None
    email_verified: bool
    name: str | None


@lru_cache
def firebase_app(project_id: str) -> firebase_admin.App:
    return firebase_admin.initialize_app(
        options={"projectId": project_id}, name=f"reference-api-{project_id}"
    )


def _verify(token: str, project_id: str) -> FirebaseIdentity:
    try:
        claims = firebase_auth.verify_id_token(
            token, app=firebase_app(project_id), check_revoked=True
        )
    except firebase_auth.CertificateFetchError as exc:
        logger.warning("firebase_certificate_fetch_failed", exc_info=True)
        raise ExternalServiceError("Could not verify the token with Firebase.") from exc
    except (
        firebase_auth.InvalidIdTokenError,  # also covers expired and revoked
        firebase_auth.UserDisabledError,
        firebase_auth.UserNotFoundError,  # e.g. the Firebase account was deleted
        ValueError,
    ):
        raise AuthenticationError("Invalid Firebase ID token.") from None
    return FirebaseIdentity(
        uid=claims["uid"],
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified", False)),
        name=claims.get("name"),
    )


async def verify_id_token(token: str, project_id: str) -> FirebaseIdentity:
    return await run_in_threadpool(_verify, token, project_id)
