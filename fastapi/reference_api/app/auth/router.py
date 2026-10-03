from fastapi import APIRouter, BackgroundTasks, Response, status

from app.auth import service
from app.auth.dependencies import CurrentUser, SettingsDep
from app.auth.firebase import verify_id_token
from app.auth.schemas import (
    ChangePasswordRequest,
    FirebaseTokenRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenOnlyRequest,
    TokenPair,
    TokenRequest,
    UserOut,
)
from app.core.db import SessionDep
from app.core.email import EmailSenderDep

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", operation_id="register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, session: SessionDep, settings: SettingsDep) -> UserOut:
    return UserOut.model_validate(await service.register(session, data, settings))


@router.post("/token", operation_id="obtainToken")
async def obtain_token(data: TokenRequest, session: SessionDep, settings: SettingsDep) -> TokenPair:
    user = await service.authenticate(session, data.email, data.password, settings)
    return await service.issue_tokens(session, user.id, settings)


@router.post("/token/refresh", operation_id="refreshToken")
async def refresh_token(
    data: RefreshRequest, session: SessionDep, settings: SettingsDep
) -> TokenPair:
    return await service.rotate(session, data.refresh, settings)


@router.post("/logout", operation_id="logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, session: SessionDep) -> Response:
    await service.logout(session, data.refresh)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", operation_id="getCurrentUser")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/firebase", operation_id="exchangeFirebaseToken")
async def exchange_firebase_token(
    data: FirebaseTokenRequest, session: SessionDep, settings: SettingsDep
) -> TokenPair:
    identity = await verify_id_token(data.id_token, settings.firebase_project_id)
    user = await service.user_for_firebase_identity(session, identity)
    return await service.issue_tokens(session, user.id, settings)


@router.post("/password", operation_id="changePassword")
async def change_password(
    data: ChangePasswordRequest, user: CurrentUser, session: SessionDep, settings: SettingsDep
) -> TokenPair:
    return await service.change_password(
        session, user, data.current_password, data.new_password, settings
    )


@router.post(
    "/password-reset", operation_id="requestPasswordReset", status_code=status.HTTP_202_ACCEPTED
)
async def request_password_reset(
    data: PasswordResetRequest,
    session: SessionDep,
    settings: SettingsDep,
    background: BackgroundTasks,
    sender: EmailSenderDep,
) -> Response:
    await service.request_password_reset(session, data.email, settings, background, sender)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/password-reset/confirm",
    operation_id="confirmPasswordReset",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def confirm_password_reset(
    data: PasswordResetConfirm, session: SessionDep, settings: SettingsDep
) -> Response:
    await service.confirm_password_reset(session, data.token, data.password, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/email-verification",
    operation_id="requestEmailVerification",
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_email_verification(
    user: CurrentUser, settings: SettingsDep, background: BackgroundTasks, sender: EmailSenderDep
) -> Response:
    service.request_email_verification(user, settings, background, sender)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/email-verification/confirm",
    operation_id="confirmEmailVerification",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def confirm_email_verification(
    data: TokenOnlyRequest, session: SessionDep, settings: SettingsDep
) -> Response:
    await service.confirm_email_verification(session, data.token, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
