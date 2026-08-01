from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

import httpx
from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.logging import configure_logging, get_logger
from app.core.module_discovery import discover_modules
from app.core.registry import (
    BotDependencies,
    BotModuleRegistry,
    RuntimeBot,
    RuntimeBotRegistry,
)
from app.core.telegram_client import TelegramBotClient, build_shared_http_client
from app.platform.bots.repositories import BotRepository
from app.platform.bots.schemas import BotConfig, BotDescriptor, BotRuntimeConfig
from app.platform.bots.services import BotConfigService
from app.platform.updates.repositories import UpdateRepository
from app.platform.updates.services import UpdateService
from app.platform.users.services import UserContextService
from app.shared.utils import keyed_fingerprint, safe_error_summary, utc_now

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: Settings
    database: Database
    http: httpx.AsyncClient
    modules: BotModuleRegistry
    runtimes: RuntimeBotRegistry
    context_service: UserContextService
    update_service: UpdateService
    started_at: datetime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    database = Database(settings)
    http = build_shared_http_client(settings)
    modules = BotModuleRegistry()
    runtimes = RuntimeBotRegistry()
    started_runtimes: list[RuntimeBot] = []
    try:
        await _connect_database(database, settings)
        await discover_modules(modules)
        config_service = BotConfigService.from_settings(database, settings)
        configs = await config_service.load_all()

        for config in configs:
            if not config.enabled:
                runtimes.add_disabled(
                    BotDescriptor(
                        id=config.id,
                        name=config.name,
                        enabled=False,
                        module_name=config.module_name,
                        description=config.description,
                    )
                )
                continue
            telegram = TelegramBotClient(http, config.token, settings)
            runtime_config = BotRuntimeConfig(
                id=config.id,
                name=config.name,
                enabled=True,
                description=config.description,
                module_name=config.module_name,
            )
            try:
                factory = modules.get(config.module_name)
                bot = factory(
                    runtime_config,
                    BotDependencies(
                        database=database,
                        settings=settings,
                        telegram=telegram,
                        http=http,
                    ),
                )
                runtime = RuntimeBot(
                    config=runtime_config,
                    bot=bot,
                    telegram=telegram,
                    secret_token=config.secret_token,
                )
            except Exception as error:
                runtime = RuntimeBot(
                    config=runtime_config,
                    bot=None,
                    telegram=telegram,
                    secret_token=config.secret_token,
                    healthy=False,
                    health_reason=safe_error_summary(error),
                )
                await logger.aerror(
                    "bot_runtime_build_failed",
                    bot_id=config.id,
                    bot_name=config.name,
                    module_name=config.module_name,
                    error_type=type(error).__name__,
                )
            runtimes.add(runtime)

        container = ApplicationContainer(
            settings=settings,
            database=database,
            http=http,
            modules=modules,
            runtimes=runtimes,
            context_service=UserContextService.build(database),
            update_service=UpdateService(database, UpdateRepository(), settings),
            started_at=utc_now(),
        )
        app.state.container = container
        enabled_configs = {config.name: config for config in configs if config.enabled}
        await asyncio.gather(
            *(
                _verify_and_sync_bot(
                    container, runtime, enabled_configs[runtime.config.name]
                )
                for runtime in runtimes.bots.values()
                if runtime.bot is not None
            )
        )
        del configs, enabled_configs, config_service
        runtimes.seal()
        for runtime in runtimes.bots.values():
            if runtime.bot is None or not runtime.healthy:
                continue
            try:
                await runtime.bot.start()
                started_runtimes.append(runtime)
            except Exception as error:
                runtimes.mark_unhealthy(
                    runtime.config.name, safe_error_summary(error)
                )
                await logger.aexception(
                    "bot_background_start_failed",
                    bot_id=runtime.config.id,
                    bot_name=runtime.config.name,
                    error_type=type(error).__name__,
                )
        await logger.ainfo(
            "application_started",
            registered_modules=len(modules),
            enabled_bots=runtimes.enabled_count,
            healthy_bots=runtimes.healthy_count,
            unhealthy_bots=runtimes.unhealthy_count,
        )
        yield
    finally:
        for runtime in reversed(started_runtimes):
            if runtime.bot is None:
                continue
            try:
                await runtime.bot.stop()
            except Exception as error:
                await logger.aexception(
                    "bot_background_stop_failed",
                    bot_id=runtime.config.id,
                    bot_name=runtime.config.name,
                    error_type=type(error).__name__,
                )
        await http.aclose()
        await database.dispose()
        await logger.ainfo("application_stopped")


async def _connect_database(database: Database, settings: Settings) -> None:
    for attempt in range(1, settings.startup_db_max_attempts + 1):
        try:
            await database.ping()
            await logger.ainfo("database_connected", attempt=attempt)
            return
        except Exception as error:
            if attempt >= settings.startup_db_max_attempts:
                await logger.aerror(
                    "database_connection_failed",
                    attempts=attempt,
                    error_type=type(error).__name__,
                )
                raise
            delay = min(
                settings.startup_db_backoff_seconds * (2 ** (attempt - 1)), 30
            )
            await logger.awarning(
                "database_connection_retry",
                attempt=attempt,
                retry_in_seconds=delay,
            )
            await asyncio.sleep(delay)


async def _verify_and_sync_bot(
    container: ApplicationContainer, runtime: RuntimeBot, stored_config: BotConfig
) -> None:
    config = runtime.config
    try:
        identity = await runtime.telegram.get_me()
        await logger.ainfo(
            "telegram_bot_identity_verified",
            bot_id=config.id,
            bot_name=config.name,
            telegram_bot_id=identity.id,
        )
        webhook = await runtime.telegram.get_webhook_info()
        expected_url = (
            f"{container.settings.webhook_base_url}/webhook/{config.name}"
        )
        expected_fingerprint = keyed_fingerprint(
            container.settings.credential_keys[0].get_secret_value(),
            expected_url,
            stored_config.secret_token.get_secret_value(),
        )
        requires_update = (
            webhook.url != expected_url
            or stored_config.webhook_url != expected_url
            or stored_config.webhook_sync_fingerprint != expected_fingerprint
        )
        if requires_update:
            await runtime.telegram.set_webhook(
                url=expected_url, secret_token=stored_config.secret_token
            )
            async with container.database.transaction() as session:
                await BotRepository().record_webhook_sync(
                    session,
                    bot_id=config.id,
                    webhook_url=expected_url,
                    fingerprint=expected_fingerprint,
                )
            await logger.ainfo(
                "telegram_webhook_updated",
                bot_id=config.id,
                bot_name=config.name,
                webhook_url=expected_url,
            )
        else:
            await logger.ainfo(
                "telegram_webhook_verified",
                bot_id=config.id,
                bot_name=config.name,
                webhook_url=expected_url,
            )
    except Exception as error:
        container.runtimes.mark_unhealthy(
            config.name, safe_error_summary(error)
        )
        await logger.aerror(
            "telegram_bot_startup_check_failed",
            bot_id=config.id,
            bot_name=config.name,
            error_type=type(error).__name__,
        )


def get_container(app: FastAPI) -> ApplicationContainer:
    return app.state.container
