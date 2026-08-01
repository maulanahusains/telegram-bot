from __future__ import annotations

from app.core.telegram_client import TelegramBotClient
from app.shared.types import TelegramCallbackQuery


async def acknowledge_callback(
    callback: TelegramCallbackQuery, telegram: TelegramBotClient
) -> None:
    await telegram.answer_callback_query(callback_query_id=callback.id)

