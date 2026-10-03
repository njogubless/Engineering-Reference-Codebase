from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User, normalize_email


def register_user(*, email: str, password: str, display_name: str) -> User:
    email = normalize_email(email)
    user = User(email=email, display_name=display_name.strip())
    try:
        # Runs Django's configured validators (length, common passwords,
        # similarity to the email/name, all-numeric).
        validate_password(password, user=user)
    except ValidationError as exc:
        # Keep each validator's own code (password_too_short, password_too_common, ...).
        raise ValidationError({"password": exc.error_list}) from None

    # Check-then-insert is racy: two requests can both pass the check. The
    # unique constraint is the real guard; the check gives the common case a
    # friendly field error, and IntegrityError covers the race.
    if User.objects.filter(email=email).exists():
        raise _duplicate_email()
    user.set_password(password)
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        raise _duplicate_email() from None
    return user


def _duplicate_email() -> ValidationError:
    # With a dict, Django ignores a top-level `code`; it must be on the inner error.
    return ValidationError(
        {"email": ValidationError("An account with this email already exists.", code="unique")}
    )
