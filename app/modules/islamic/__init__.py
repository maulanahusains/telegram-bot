from __future__ import annotations

from app.core.registry import BaseBot, BotDependencies, BotModuleRegistry
from app.modules.islamic.api import IslamicAPIClient
from app.modules.islamic.bot import IslamicBot
from app.modules.islamic.repositories import IslamicRepository
from app.modules.islamic.router import IslamicRouter
from app.modules.islamic.schemas import PrayerClaim
from app.modules.islamic.services import IslamicScheduler, IslamicService
from app.platform.bots.schemas import BotRuntimeConfig


def _factory(config: BotRuntimeConfig, dependencies: BotDependencies) -> BaseBot:
    api = IslamicAPIClient(dependencies.http)
    service = IslamicService(
        dependencies.database, IslamicRepository(), api, config.id
    )
    router = IslamicRouter(service, api, dependencies.telegram)
    bot: IslamicBot

    async def deliver(claim: PrayerClaim) -> None:
        await bot.deliver_reminder(claim)

    async def cleanup(chat_id: int, message_ids: list[int]) -> None:
        await bot.cleanup_messages(chat_id, message_ids)

    scheduler = IslamicScheduler(service, deliver, cleanup)
    bot = IslamicBot(router, service, scheduler, dependencies.telegram)
    return bot


def register(registry: BotModuleRegistry) -> None:
    registry.register(name="islamic", factory=_factory)
