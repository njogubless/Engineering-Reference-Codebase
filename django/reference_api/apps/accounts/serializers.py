from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.serializers import PasswordField, TokenObtainPairSerializer

from apps.accounts.models import User
from apps.core.serializers import StrictInputMixin


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("id", "email", "display_name", "date_joined")
        read_only_fields = fields


class RegisterSerializer(StrictInputMixin, serializers.Serializer):  # type: ignore[type-arg]
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        min_length=10, max_length=128, write_only=True, trim_whitespace=False
    )
    display_name = serializers.CharField(min_length=1, max_length=100)


class ObtainTokenSerializer(TokenObtainPairSerializer):
    """simplejwt's password field trims whitespace (DRF's CharField default),
    while registration must not: a password ending in a space could be set
    but never used to log in. Found by Schemathesis."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password"] = PasswordField(trim_whitespace=False)


class LogoutSerializer(StrictInputMixin, serializers.Serializer):  # type: ignore[type-arg]
    refresh = serializers.CharField(max_length=1024)
