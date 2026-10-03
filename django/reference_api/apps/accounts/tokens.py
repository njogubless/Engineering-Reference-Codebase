"""Single-use, expiring tokens for email links, built on Django's
PasswordResetTokenGenerator.

The generator signs a hash of user *state*. A token stops working as soon as
that state changes, which makes it single-use without storing anything:
- password reset: the hash includes the password hash and last login, so
  using the token (changing the password) invalidates it;
- email verification: the hash includes the email and the verified flag, so
  verifying, or changing the email, invalidates it.

The emailed value is "<uid>.<token>", so one field carries both.
"""

from typing import Any

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.accounts.models import User


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "apps.accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user: Any, timestamp: int) -> str:
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


password_reset_tokens = PasswordResetTokenGenerator()
email_verification_tokens = EmailVerificationTokenGenerator()


def make_link_token(generator: PasswordResetTokenGenerator, user: User) -> str:
    return f"{urlsafe_base64_encode(force_bytes(user.pk))}.{generator.make_token(user)}"


def user_from_link_token(generator: PasswordResetTokenGenerator, value: str) -> User | None:
    """The user the token was issued for, or None if it is malformed, expired or used."""
    uid, _, token = value.partition(".")
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    # ValidationError: a decodable id that is not a UUID (e.g. a tampered token).
    except (ValueError, TypeError, OverflowError, ValidationError, User.DoesNotExist):
        return None
    return user if generator.check_token(user, token) else None
