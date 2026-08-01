from __future__ import annotations

from app.core.registry import BaseBot
from app.modules.sample_bot.router import SampleRouter
from app.shared.types import ChatContext, TelegramUpdate, UserContext


class SampleBot(BaseBot):
    def __init__(self, router: SampleRouter) -> None:
        self._router = router

    async def handle_update(
        self, update: TelegramUpdate, context: UserContext | ChatContext
    ) -> None:
        if isinstance(context, ChatContext):
            return
        await self._router.dispatch(update, context)

