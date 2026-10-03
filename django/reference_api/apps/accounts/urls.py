from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("auth/register", views.RegisterView.as_view(), name="auth-register"),
    path("auth/token", views.ObtainTokenView.as_view(), name="auth-token"),
    path("auth/token/refresh", views.RefreshTokenView.as_view(), name="auth-token-refresh"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me", views.MeView.as_view(), name="auth-me"),
    path("auth/firebase", views.FirebaseExchangeView.as_view(), name="auth-firebase"),
    path("auth/password", views.ChangePasswordView.as_view(), name="auth-password"),
    path(
        "auth/password-reset", views.PasswordResetRequestView.as_view(), name="auth-password-reset"
    ),
    path(
        "auth/password-reset/confirm",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path(
        "auth/email-verification", views.EmailVerificationRequestView.as_view(), name="auth-verify"
    ),
    path(
        "auth/email-verification/confirm",
        views.EmailVerificationConfirmView.as_view(),
        name="auth-verify-confirm",
    ),
]
