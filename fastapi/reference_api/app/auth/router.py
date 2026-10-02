from fastapi import APIRouter, Response, status

from app.auth import service
from app.auth.dependencies import CurrentUser, SettingsDep
from app.auth.schemas import RefreshRequest, RegisterRequest, TokenPair, TokenRequest, UserOut
from app.core.db import SessionDep

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
