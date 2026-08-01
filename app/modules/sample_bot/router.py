from __future__ import annotations

from app.core.telegram_client import TelegramBotClient
from app.modules.sample_bot.handlers.callback import acknowledge_callback
from app.modules.sample_bot.handlers.message import (
    handle_counter,
    handle_me,
    handle_ping,
    handle_start,
)
from app.modules.sample_bot.schemas import SampleCommand
from app.modules.sample_bot.services.sample_service import SampleService
from app.shared.types import TelegramUpdate, UserContext


class SampleRouter:
    def __init__(
        self, service: SampleService, telegram: TelegramBotClient
    ) -> None:
        self._service = service
        self._telegram = telegram

    async def dispatch(self, update: TelegramUpdate, context: UserContext) -> None:
        if update.callback_query is not None:
            await acknowledge_callback(update.callback_query, self._telegram)
            return
        message = update.effective_message()
        if message is None or message.text is None:
            return
        command = message.text.strip().split(maxsplit=1)[0].lower().split("@", 1)[0]
        if command == SampleCommand.START:
            await handle_start(context, self._service, self._telegram)
        elif command == SampleCommand.PING:
            await handle_ping(context, self._service, self._telegram)
        elif command == SampleCommand.ME:
            await handle_me(context, self._service, self._telegram)
        elif command == SampleCommand.COUNTER:
            await handle_counter(
                context, self._service, self._telegram, update.update_id
            )
