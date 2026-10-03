"""Transactional emails. Sent after the database transaction commits:
an email must never announce something that was rolled back.

Phase 10 moves sending onto a Celery queue with retries; until then a
failed SMTP call is logged and the request still succeeds (the user can ask
for a new link).
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from apps.accounts.models import User
from apps.accounts.tokens import email_verification_tokens, make_link_token, password_reset_tokens

logger = logging.getLogger(__name__)


def _link(path: str, token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL}{path}?{urlencode({'token': token})}"


def _send_after_commit(subject: str, body: str, recipient: str, kind: str) -> None:
    def send() -> None:
        try:
            send_mail(subject, body, None, [recipient])
        except OSError:
            # Never log the link: it is a credential.
            logger.exception("email_send_failed", extra={"kind": kind})

    transaction.on_commit(send)


def send_password_reset(user: User) -> None:
    assert user.email is not None  # noqa: S101 - callers look users up by email
    link = _link("/reset-password", make_link_token(password_reset_tokens, user))
    _send_after_commit(
        "Reset your password",
        f"Someone asked to reset the password for this account.\n\n{link}\n\n"
        "The link works once and expires in one hour. If it wasn't you, ignore this email.",
        user.email,
        kind="password_reset",
    )


def send_email_verification(user: User) -> None:
    assert user.email is not None  # noqa: S101 - verified only when an email exists
    link = _link("/verify-email", make_link_token(email_verification_tokens, user))
    _send_after_commit(
        "Confirm your email address",
        f"Confirm this address for your account:\n\n{link}",
        user.email,
        kind="email_verification",
    )
