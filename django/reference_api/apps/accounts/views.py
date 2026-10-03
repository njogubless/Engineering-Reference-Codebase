"""Authentication endpoints.

Token issuing and rotation come from djangorestframework-simplejwt — the
idiomatic Django choice. The FastAPI reference implements the same contract
by hand to show the mechanics (fastapi/reference_api/app/auth/).
"""

import contextlib

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts import services
from apps.accounts.firebase import verify_id_token
from apps.accounts.request import require_user
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    FirebaseTokenSerializer,
    LogoutSerializer,
    ObtainTokenSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TokenOnlySerializer,
    UserSerializer,
)
from apps.accounts.services import register_user
from apps.core.views import PublicAPIView


class RegisterView(PublicAPIView):
    @extend_schema(
        operation_id="register", request=RegisterSerializer, responses={201: UserSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(operation_id="obtainToken")
class ObtainTokenView(TokenObtainPairView):
    """Wrong email and wrong password produce the same 401: no account enumeration."""

    serializer_class = ObtainTokenSerializer


@extend_schema(operation_id="refreshToken")
class RefreshTokenView(TokenRefreshView):
    """Rotation: every refresh returns a new refresh token and blacklists the old one."""


class LogoutView(PublicAPIView):
    @extend_schema(operation_id="logout", request=LogoutSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Expired, malformed or already revoked: nothing left to revoke.
        # Logout stays idempotent, so a retried logout never shows an error.
        with contextlib.suppress(TokenError):
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="getCurrentUser", responses=UserSerializer)
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(require_user(request)).data)


class FirebaseExchangeView(PublicAPIView):
    @extend_schema(operation_id="exchangeFirebaseToken", request=FirebaseTokenSerializer)
    def post(self, request: Request) -> Response:
        serializer = FirebaseTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identity = verify_id_token(serializer.validated_data["id_token"])
        user = services.user_for_firebase_identity(identity)
        return Response(services.token_pair(user))


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="changePassword", request=ChangePasswordSerializer)
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = require_user(request)
        services.change_password(user=user, **serializer.validated_data)
        # Every session was revoked; this one gets fresh tokens.
        return Response(services.token_pair(user))


class PasswordResetRequestView(PublicAPIView):
    @extend_schema(
        operation_id="requestPasswordReset",
        request=PasswordResetRequestSerializer,
        responses={202: None},
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(email=serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(PublicAPIView):
    @extend_schema(
        operation_id="confirmPasswordReset",
        request=PasswordResetConfirmSerializer,
        responses={204: None},
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_password_reset(**serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailVerificationRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="requestEmailVerification", request=None, responses={202: None})
    def post(self, request: Request) -> Response:
        services.request_email_verification(user=require_user(request))
        return Response(status=status.HTTP_202_ACCEPTED)


class EmailVerificationConfirmView(PublicAPIView):
    @extend_schema(
        operation_id="confirmEmailVerification", request=TokenOnlySerializer, responses={204: None}
    )
    def post(self, request: Request) -> Response:
        serializer = TokenOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_email_verification(token=serializer.validated_data["token"])
        return Response(status=status.HTTP_204_NO_CONTENT)
