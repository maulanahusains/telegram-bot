from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.lifespan import get_container
from app.core.logging import bind_contextvars, get_logger
from app.platform.bots.services import BOT_NAME_PATTERN
from app.platform.updates.repositories import ClaimResult
from app.shared.exceptions import (
    BotNotFoundError,
    InvalidTelegramSecretError,
    InvalidUpdateError,
    UserBlockedError,
)
from app.shared.responses import success
from app.shared.types import ChatContext, TelegramUpdate, UserContext
from app.shared.utils import constant_time_equal

router = APIRouter()
logger = get_logger(__name__)


@router.post("/webhook/{bot_name}")
async def telegram_webhook(bot_name: str, request: Request) -> JSONResponse:
    started = time.perf_counter()
    if BOT_NAME_PATTERN.fullmatch(bot_name) is None:
        raise BotNotFoundError

    container = get_container(request.app)
    runtime = container.runtimes.get(bot_name)
    provided_secret = request.headers.get("x-telegram-bot-api-secret-token")
    if provided_secret is None or not constant_time_equal(
        provided_secret, runtime.secret_token.get_secret_value()
    ):
        raise InvalidTelegramSecretError

    content_type = request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        return _safe_error(
            request, 415, "unsupported_media_type", "Expected application/json."
        )
    body = await _read_limited_body(
        request, container.settings.webhook_body_limit_bytes
    )
    try:
        update = TelegramUpdate.model_validate_json(body)
    except ValidationError as error:
        raise InvalidUpdateError from error

    bind_contextvars(
        bot_id=runtime.config.id,
        bot_name=runtime.config.name,
        update_id=update.update_id,
        update_type=update.update_type(),
    )
    await logger.ainfo("incoming_telegram_webhook")
    claim = await container.update_service.claim(runtime.config.id, update)
    if claim.result is not ClaimResult.CLAIMED:
        await logger.ainfo(
            "duplicate_update_ignored",
            processing_status=claim.result.value,
            attempts=claim.attempts,
        )
        return JSONResponse(
            status_code=200, content=success(status=claim.result.value)
        )

    try:
        context = await container.context_service.resolve(runtime.config, update)
        if context is None:
            await container.update_service.processed(claim)
            return JSONResponse(status_code=200, content=success(status="ignored"))
        if isinstance(context, UserContext):
            bind_contextvars(
                internal_user_id=context.internal_user_id,
                telegram_user_id=context.telegram_user_id,
                bot_user_id=context.bot_user_id,
                chat_id=context.chat_id,
            )
        elif isinstance(context, ChatContext):
            bind_contextvars(chat_id=context.chat_id)
        if runtime.bot is None:
            raise RuntimeError("Runtime bot is unavailable")
        await runtime.bot.handle_update(update, context)
        await container.update_service.processed(claim)
        await logger.ainfo(
            "telegram_update_processed",
            processing_status="processed",
            execution_time_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return JSONResponse(status_code=200, content=success())
    except UserBlockedError:
        await container.update_service.processed(claim)
        await logger.ainfo("telegram_update_ignored", processing_status="blocked")
        return JSONResponse(status_code=200, content=success(status="blocked"))
    except Exception as error:
        exhausted = await container.update_service.failed(claim, error)
        await logger.aexception(
            "telegram_update_processing_failed",
            processing_status="failed",
            attempts=claim.attempts,
            exhausted=exhausted,
            error_type=type(error).__name__,
            execution_time_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        if exhausted:
            return JSONResponse(
                status_code=200, content=success(status="failed_exhausted")
            )
        return _safe_error(
            request, 500, "update_processing_failed", "Update processing failed."
        )


async def _read_limited_body(request: Request, limit: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > limit:
                return _raise_body_too_large()
        except ValueError:
            return _raise_invalid_content_length()
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return _raise_body_too_large()
        chunks.append(chunk)
    return b"".join(chunks)


def _raise_body_too_large() -> bytes:
    from starlette.exceptions import HTTPException

    raise HTTPException(status_code=413, detail="Request body is too large.")


def _raise_invalid_content_length() -> bytes:
    from starlette.exceptions import HTTPException

    raise HTTPException(status_code=400, detail="Invalid Content-Length.")


def _safe_error(
    request: Request, status_code: int, code: str, message: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )
