"""Custom user model.

Set a custom user model before the first migration, even if it adds nothing:
switching later means rewriting the auth tables of a live database. Here it
replaces username login with email login and uses UUIDv7 keys.
"""

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

from apps.core.ids import uuid7


def normalize_email(email: str) -> str:
    """One canonical form, so `Ann@Example.com` and `ann@example.com` are one account."""
    return email.strip().lower()


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        user = self.model(email=normalize_email(email), **extra)
        user.set_password(password)  # None -> unusable password (e.g. social-only accounts)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        extra.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)

    def get_by_natural_key(self, username: str | None) -> "User":
        # Login looks users up through this. Emails are stored normalised, so
        # normalise the input and match exactly: that uses the unique index.
        # (`email__iexact` compiles to UPPER(email) = UPPER(%s), which cannot
        # use it and scans the whole table on every login.)
        return self.get(email=normalize_email(username or ""))


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    username = None  # type: ignore[assignment]
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["display_name"]

    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    class Meta:
        constraints: ClassVar = [
            # Guards case-insensitive uniqueness even if a write bypasses normalize_email().
            # Lookups use the plain unique index on `email` (values are stored lowercased).
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.email
