from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from app.core.config import Settings
from app.shared.exceptions import TelegramAPIError

T = TypeVar("T")


class TelegramResponse(BaseModel, Generic[T]):
    ok: bool
    result: T | None = None
    error_code: int | None = None
    description: str | None = None
    parameters: dict[str, Any] | None = None


class TelegramBotIdentity(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    is_bot: bool
    first_name: str
    username: str | None = None


class WebhookInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    has_custom_certificate: bool = False
    pending_update_count: int = 0
    last_error_date: int | None = None
    last_error_message: str | None = None
    max_connections: int | None = None
    allowed_updates: list[str] | None = None


class SentMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    message_id: int
    date: int
    chat: dict[str, Any]
    text: str | None = None


@dataclass(frozen=True, slots=True)
class InputFile:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class TelegramBotClient:
    def __init__(
        self, http: httpx.AsyncClient, token: SecretStr, settings: Settings
    ) -> None:
        self._http = http
        self._token = token
        self._settings = settings

    @property
    def _base_url(self) -> str:
        return f"https://api.telegram.org/bot{self._token.get_secret_value()}"

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> SentMessage:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._typed_request(
            "sendMessage", payload, SentMessage, safe_retry=False
        )

    async def edit_message(
        self,
        *,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> SentMessage:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._typed_request(
            "editMessageText",
            payload,
            SentMessage,
            safe_retry=False,
        )

    async def delete_message(self, *, chat_id: int, message_id: int) -> bool:
        return await self._typed_request(
            "deleteMessage",
            {"chat_id": chat_id, "message_id": message_id},
            bool,
            safe_retry=False,
        )

    async def answer_callback_query(
        self, *, callback_query_id: str, text: str | None = None
    ) -> bool:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text is not None:
            payload["text"] = text
        return await self._typed_request(
            "answerCallbackQuery", payload, bool, safe_retry=False
        )

    async def send_photo(
        self,
        *,
        chat_id: int,
        photo: str | InputFile,
        caption: str | None = None,
    ) -> SentMessage:
        return await self._send_media(
            "sendPhoto", "photo", chat_id, photo, caption, SentMessage
        )

    async def send_document(
        self,
        *,
        chat_id: int,
        document: str | InputFile,
        caption: str | None = None,
    ) -> SentMessage:
        return await self._send_media(
            "sendDocument", "document", chat_id, document, caption, SentMessage
        )

    async def send_chat_action(self, *, chat_id: int, action: str) -> bool:
        return await self._typed_request(
            "sendChatAction",
            {"chat_id": chat_id, "action": action},
            bool,
            safe_retry=False,
        )

    async def get_me(self) -> TelegramBotIdentity:
        return await self._typed_request(
            "getMe", {}, TelegramBotIdentity, safe_retry=True
        )

    async def get_webhook_info(self) -> WebhookInfo:
        return await self._typed_request(
            "getWebhookInfo", {}, WebhookInfo, safe_retry=True
        )

    async def set_webhook(
        self,
        *,
        url: str,
        secret_token: SecretStr,
        drop_pending_updates: bool = False,
    ) -> bool:
        return await self._typed_request(
            "setWebhook",
            {
                "url": url,
                "secret_token": secret_token.get_secret_value(),
                "drop_pending_updates": drop_pending_updates,
            },
            bool,
            safe_retry=True,
        )

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> bool:
        return await self._typed_request(
            "deleteWebhook",
            {"drop_pending_updates": drop_pending_updates},
            bool,
            safe_retry=True,
        )

    async def _send_media(
        self,
        method: str,
        field: str,
        chat_id: int,
        media: str | InputFile,
        caption: str | None,
        result_type: type[T],
    ) -> T:
        data: dict[str, Any] = {"chat_id": str(chat_id)}
        if caption is not None:
            data["caption"] = caption
        files: dict[str, tuple[str, bytes, str]] | None = None
        if isinstance(media, InputFile):
            files = {
                field: (media.filename, media.content, media.content_type)
            }
        else:
            data[field] = media
        raw = await self._request(
            method, data=data, files=files, safe_retry=False
        )
        return self._validate_result(raw, result_type)

    async def _typed_request(
        self,
        method: str,
        payload: dict[str, Any],
        result_type: type[T],
        *,
        safe_retry: bool,
    ) -> T:
        raw = await self._request(method, json=payload, safe_retry=safe_retry)
        return self._validate_result(raw, result_type)

    async def _request(
        self,
        method: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        safe_retry: bool,
    ) -> TelegramResponse[Any]:
        attempts = self._settings.telegram_safe_retry_attempts if safe_retry else 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._http.post(
                    f"{self._base_url}/{method}",
                    json=json,
                    data=data,
                    files=files,
                )
                try:
                    envelope = TelegramResponse[Any].model_validate(response.json())
                except (ValueError, TypeError):
                    if (
                        safe_retry
                        and attempt < attempts
                        and response.status_code in (429, 500, 502, 503, 504)
                    ):
                        await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
                        continue
                    raise TelegramAPIError from None
                if envelope.ok:
                    return envelope
                retry_after = (
                    envelope.parameters.get("retry_after")
                    if envelope.parameters
                    else None
                )
                error = TelegramAPIError(
                    telegram_error_code=envelope.error_code,
                    retry_after=retry_after if isinstance(retry_after, int) else None,
                )
                if (
                    not safe_retry
                    or attempt >= attempts
                    or envelope.error_code not in (429, 500, 502, 503, 504)
                ):
                    raise error
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as error:
                if not safe_retry or attempt >= attempts:
                    raise TelegramAPIError from None
            except (ValueError, TypeError):
                raise TelegramAPIError from None
            await asyncio.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))
        raise TelegramAPIError

    @staticmethod
    def _validate_result(envelope: TelegramResponse[Any], result_type: type[T]) -> T:
        result = envelope.result
        if result_type is bool:
            if not isinstance(result, bool):
                raise TelegramAPIError
            return result  # type: ignore[return-value]
        if not isinstance(result_type, type) or not issubclass(result_type, BaseModel):
            return result  # type: ignore[return-value]
        return result_type.model_validate(result)


def build_shared_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            timeout=settings.telegram_http_timeout,
            connect=settings.telegram_http_connect_timeout,
        ),
        limits=httpx.Limits(
            max_connections=settings.telegram_http_max_connections,
            max_keepalive_connections=settings.telegram_http_keepalive_connections,
        ),
        headers={"User-Agent": f"{settings.app_name}/{settings.app_version}"},
    )
