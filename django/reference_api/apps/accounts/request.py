from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request

from apps.accounts.models import User


def require_user(request: Request) -> User:
    """The authenticated user, typed as `User`.

    Views with `IsAuthenticated` permissions never reach this without a user;
    the check makes that guarantee explicit (and visible to the type checker)
    instead of trusting a cast.
    """
    user = request.user
    if not isinstance(user, User):
        raise NotAuthenticated
    return user
