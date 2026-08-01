from __future__ import annotations

from app.core.registry import (
    BaseBot,
    BotDependencies,
    BotModuleRegistry,
)
from app.modules.sample_bot.bot import SampleBot
from app.modules.sample_bot.repositories.sample_repository import SampleRepository
from app.modules.sample_bot.router import SampleRouter
from app.modules.sample_bot.services.sample_service import SampleService
from app.platform.bots.schemas import BotRuntimeConfig
from app.platform.users.repositories import UserStateRepository
from app.platform.users.services import UserStateService


def _factory(config: BotRuntimeConfig, dependencies: BotDependencies) -> BaseBot:
    state_service = UserStateService(
        dependencies.database,
        UserStateRepository(),
        dependencies.settings.state_conflict_retries,
    )
    service = SampleService(
        dependencies.database,
        SampleRepository(),
        state_service,
    )
    router = SampleRouter(service, dependencies.telegram)
    return SampleBot(router)


def register(registry: BotModuleRegistry) -> None:
    registry.register(name="sample", factory=_factory)
