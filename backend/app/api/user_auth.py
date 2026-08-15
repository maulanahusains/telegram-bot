from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.lifespan import get_container
from app.platform.auth.dependencies import Authenticated
from app.platform.auth.schemas import (
    AuthBootstrapResponse,
    CurrentUserResponse,
    SessionBootstrap,
    TelegramMiniAppAuthRequest,
    public_user,
)
from app.platform.auth.services import PlatformAuthService
from app.platform.bots.services import BOT_NAME_PATTERN
from app.shared.exceptions import (
    BotDisabledError,
    BotNotFoundError,
    BotUnavailableError,
    InvalidTelegramInitDataError,
)
from app.shared.responses import SuccessResponse

router = APIRouter(prefix="/api/v1", tags=["User authentication"])


@router.post("/auth/telegram", response_model=AuthBootstrapResponse)
async def authenticate_telegram_mini_app(
    data: TelegramMiniAppAuthRequest, request: Request, response: Response
) -> AuthBootstrapResponse:
    if BOT_NAME_PATTERN.fullmatch(data.launching_bot_name) is None:
        raise InvalidTelegramInitDataError
    container = get_container(request.app)
    try:
        runtime = container.runtimes.get(data.launching_bot_name)
    except (BotNotFoundError, BotDisabledError, BotUnavailableError) as error:
        raise InvalidTelegramInitDataError from error

    issued = await PlatformAuthService(
        container.database, container.settings
    ).authenticate_telegram_mini_app(runtime, data.init_data)
    _set_session_cookie(response, request, issued.token)
    return AuthBootstrapResponse(
        user=public_user(issued.user),
        session=SessionBootstrap(expires_at=issued.user.session_expires_at),
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(authenticated_user: Authenticated) -> CurrentUserResponse:
    return public_user(authenticated_user)


@router.post("/auth/logout", response_model=SuccessResponse)
async def logout(request: Request, response: Response) -> SuccessResponse:
    container = get_container(request.app)
    token = request.cookies.get(container.settings.application_session_cookie_name)
    await PlatformAuthService(container.database, container.settings).logout(token)
    response.delete_cookie(
        key=container.settings.application_session_cookie_name,
        path="/api/v1",
        secure=container.settings.application_session_cookie_secure,
        httponly=True,
        samesite=container.settings.application_session_cookie_samesite,
    )
    return SuccessResponse(status="logged_out")


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    settings = get_container(request.app).settings
    response.set_cookie(
        key=settings.application_session_cookie_name,
        value=token,
        max_age=settings.application_session_ttl_seconds,
        httponly=True,
        secure=settings.application_session_cookie_secure,
        samesite=settings.application_session_cookie_samesite,
        path="/api/v1",
    )
