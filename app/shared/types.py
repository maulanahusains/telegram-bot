from __future__ import annotations

from types import MappingProxyType
from typing import Any, Literal, Mapping, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    is_bot: bool = False
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    type: Literal["private", "group", "supergroup", "channel"]
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TelegramLocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    latitude: float
    longitude: float


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    message_id: int
    date: int
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    sender_chat: TelegramChat | None = None
    text: str | None = None
    caption: str | None = None
    location: TelegramLocation | None = None
    reply_to_message: TelegramMessage | None = None


class TelegramCallbackQuery(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    from_user: TelegramUser = Field(alias="from")
    message: TelegramMessage | None = None
    data: str | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    update_id: int
    message: TelegramMessage | None = None
    edited_message: TelegramMessage | None = None
    channel_post: TelegramMessage | None = None
    edited_channel_post: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None

    def effective_message(self) -> TelegramMessage | None:
        return (
            self.message
            or self.edited_message
            or self.channel_post
            or self.edited_channel_post
            or (self.callback_query.message if self.callback_query else None)
        )

    def effective_user(self) -> TelegramUser | None:
        if self.callback_query is not None:
            return self.callback_query.from_user
        message = self.effective_message()
        return message.from_user if message is not None else None

    def effective_chat(self) -> TelegramChat | None:
        message = self.effective_message()
        return message.chat if message is not None else None

    def update_type(self) -> str:
        for name in (
            "message",
            "edited_message",
            "channel_post",
            "edited_channel_post",
            "callback_query",
        ):
            if getattr(self, name) is not None:
                return name
        extra = self.model_extra or {}
        return next(iter(extra), "unknown")


class SessionState(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: str | None = None
    data: Mapping[str, Any] = Field(default_factory=dict)
    version: int = 0

    @classmethod
    def immutable(
        cls, *, state: str | None, data: dict[str, Any], version: int
    ) -> SessionState:
        return cls(state=state, data=MappingProxyType(dict(data)), version=version)


class UserContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    bot_id: int
    bot_name: str
    telegram_user_id: int
    internal_user_id: int
    bot_user_id: int
    chat_id: int
    chat_type: str
    username: str | None
    first_name: str
    last_name: str | None
    language_code: str | None
    user_status: str
    user_role: str
    session_state: SessionState


class ChatContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    bot_id: int
    bot_name: str
    chat_id: int
    chat_type: str
    chat_title: str | None
    chat_username: str | None


BotContext: TypeAlias = UserContext | ChatContext
