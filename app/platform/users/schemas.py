from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelegramUserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_user_id: int
    username: str | None
    first_name: str
    last_name: str | None
    language_code: str | None


class BotUserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int
    user_id: int
    status: str
    role: str
    locale: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_")


class UserStateValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: str | None
    data: dict[str, Any]
    version: int

