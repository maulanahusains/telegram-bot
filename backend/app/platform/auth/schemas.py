from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TelegramMiniAppAuthRequest(BaseModel):
    launching_bot_name: str = Field(min_length=1, max_length=64)
    init_data: str = Field(min_length=1, max_length=8192)


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: int
    telegram_user_id: int
    username: str | None
    first_name: str
    last_name: str | None
    language_code: str | None
    launching_bot_id: int
    launching_bot_name: str
    launching_bot_module_name: str
    session_expires_at: datetime


class LaunchingBotPublic(BaseModel):
    name: str
    module_name: str


class CurrentUserResponse(BaseModel):
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    launching_bot: LaunchingBotPublic
    session_expires_at: datetime


class SessionBootstrap(BaseModel):
    authenticated: bool = True
    expires_at: datetime


class AuthBootstrapResponse(BaseModel):
    user: CurrentUserResponse
    session: SessionBootstrap


def public_user(value: AuthenticatedUser) -> CurrentUserResponse:
    return CurrentUserResponse(
        first_name=value.first_name,
        last_name=value.last_name,
        username=value.username,
        language_code=value.language_code,
        launching_bot=LaunchingBotPublic(
            name=value.launching_bot_name,
            module_name=value.launching_bot_module_name,
        ),
        session_expires_at=value.session_expires_at,
    )
