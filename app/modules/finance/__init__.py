from __future__ import annotations

from app.core.registry import BaseBot, BotDependencies, BotModuleRegistry
from app.modules.finance.bot import FinanceBot
from app.modules.finance.repositories import FinanceRepository
from app.modules.finance.router import FinanceRouter
from app.modules.finance.schemas import AlertClaim
from app.modules.finance.services import FinanceAlertScheduler, FinanceService
from app.platform.bots.schemas import BotRuntimeConfig


def _factory(config: BotRuntimeConfig, dependencies: BotDependencies) -> BaseBot:
    service = FinanceService(
        dependencies.database, FinanceRepository(), config.id
    )
    router = FinanceRouter(service, dependencies.telegram)
    bot: FinanceBot

    async def deliver(claim: AlertClaim) -> None:
        await bot.deliver_alert(claim)

    scheduler = FinanceAlertScheduler(service, deliver)
    bot = FinanceBot(router, scheduler, dependencies.telegram)
    return bot


def register(registry: BotModuleRegistry) -> None:
    registry.register(name="finance", factory=_factory)
