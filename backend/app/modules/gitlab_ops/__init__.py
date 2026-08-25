from __future__ import annotations

from app.core.registry import BaseBot, BotDependencies, BotModuleRegistry
from app.modules.gitlab_ops.bot import GitlabOpsBot
from app.modules.gitlab_ops.repositories import GitlabOpsRepository
from app.modules.gitlab_ops.router import GitlabOpsRouter
from app.modules.gitlab_ops.services import GitlabOpsService
from app.platform.bots.schemas import BotRuntimeConfig
from app.platform.bots.services import CredentialCipher
from app.platform.users.services import UserStateService
from app.platform.users.repositories import UserStateRepository


def _factory(config: BotRuntimeConfig, dependencies: BotDependencies) -> BaseBot:
    repository = GitlabOpsRepository()
    cipher = CredentialCipher(dependencies.settings.credential_keys)
    state = UserStateService(
        dependencies.database,
        repository=UserStateRepository(),
        conflict_retries=dependencies.settings.state_conflict_retries,
    )
    service = GitlabOpsService(
        database=dependencies.database,
        repository=repository,
        cipher=cipher,
        http=dependencies.http,
        settings=dependencies.settings,
        bot_id=config.id,
    )
    router = GitlabOpsRouter(service, state, dependencies.telegram)
    return GitlabOpsBot(
        router=router,
        service=service,
        telegram=dependencies.telegram,
        executor_enabled=dependencies.settings.gitlab_ops_executor_enabled,
        executor_interval_seconds=dependencies.settings.gitlab_ops_executor_interval_seconds,
        executor_batch_size=dependencies.settings.gitlab_ops_executor_batch_size,
    )


def register(registry: BotModuleRegistry) -> None:
    registry.register(name="gitlab_ops", factory=_factory)
