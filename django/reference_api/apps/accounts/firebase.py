"""Firebase ID-token verification.

    Flutter/React ─ Firebase Auth ─► ID token ─► POST /api/v1/auth/firebase
                                                   │ verify signature (Google's keys),
                                                   │ audience = our project, issuer,
                                                   │ expiry, and revocation
                                                   ▼
                                     FirebaseIdentity(uid, email, email_verified)

The uid is the only identity the server trusts. Anything else the client
sends ("my uid is X", "my email is Y") is ignored by construction: the
request schema has a single field, the token.

Emulator: when FIREBASE_AUTH_EMULATOR_HOST is set, firebase-admin accepts
the emulator's *unsigned* tokens, so anyone can mint one (the tests forge a
subject and only the user lookup stops it). Settings therefore refuse that
variable in staging/production.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache

import firebase_admin
from django.conf import settings
from firebase_admin import auth as firebase_auth
from rest_framework.exceptions import AuthenticationFailed

from apps.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str | None
    email_verified: bool
    name: str | None


@lru_cache
def _app() -> firebase_admin.App:
    # A named app with only the project id: verifying ID tokens needs no
    # credentials (Google's public keys are fetched). Revocation checks do;
    # in production they come from the platform's default credentials.
    return firebase_admin.initialize_app(
        options={"projectId": settings.FIREBASE_PROJECT_ID}, name="reference-api"
    )


def verify_id_token(token: str) -> FirebaseIdentity:
    try:
        claims = firebase_auth.verify_id_token(token, app=_app(), check_revoked=True)
    except firebase_auth.CertificateFetchError as exc:
        # Our problem (network/Google), not the client's: 502, not 401.
        logger.warning("firebase_certificate_fetch_failed", exc_info=True)
        raise ExternalServiceError("Could not verify the token with Firebase.") from exc
    except (
        firebase_auth.InvalidIdTokenError,  # also covers expired and revoked
        firebase_auth.UserDisabledError,
        firebase_auth.UserNotFoundError,  # e.g. the Firebase account was deleted
        ValueError,
    ):
        raise AuthenticationFailed("Invalid Firebase ID token.") from None
    return FirebaseIdentity(
        uid=claims["uid"],
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified", False)),
        name=claims.get("name"),
    )
