from __future__ import annotations

from app.core.telegram_client import TelegramBotClient
from app.modules.sample_bot.services.sample_service import SampleService
from app.shared.types import UserContext


async def handle_start(
    context: UserContext, service: SampleService, telegram: TelegramBotClient
) -> None:
    await service.record_command(context.bot_user_id)
    await telegram.send_message(chat_id=context.chat_id, text="Welcome.")


async def handle_ping(
    context: UserContext, service: SampleService, telegram: TelegramBotClient
) -> None:
    await service.record_command(context.bot_user_id)
    await telegram.send_message(chat_id=context.chat_id, text="pong")


async def handle_me(
    context: UserContext, service: SampleService, telegram: TelegramBotClient
) -> None:
    await service.record_command(context.bot_user_id)
    text = "\n".join(
        (
            f"Internal user ID: {context.internal_user_id}",
            f"Telegram user ID: {context.telegram_user_id}",
            f"Bot user ID: {context.bot_user_id}",
            f"Bot name: {context.bot_name}",
            f"User role: {context.user_role}",
            f"User status: {context.user_status}",
        )
    )
    await telegram.send_message(chat_id=context.chat_id, text=text)


async def handle_counter(
    context: UserContext,
    service: SampleService,
    telegram: TelegramBotClient,
    update_id: int,
) -> None:
    await service.record_command(context.bot_user_id)
    value = await service.increment_counter(context.bot_user_id, update_id)
    await telegram.send_message(chat_id=context.chat_id, text=f"Counter: {value}")
