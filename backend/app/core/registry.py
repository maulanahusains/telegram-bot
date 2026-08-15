from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

import httpx
from pydantic import SecretStr

from app.core.config import Settings
from app.core.database import Database
from app.core.telegram_client import TelegramBotClient
from app.platform.bots.schemas import BotDescriptor, BotRuntimeConfig
from app.shared.exceptions import (
    BotDisabledError,
    BotNotFoundError,
    BotUnavailableError,
    InvalidBotModuleError,
)
from app.shared.types import BotContext, TelegramUpdate


class BaseBot(ABC):
    async def start(self) -> None:
        """Start optional module-owned background work."""

    async def stop(self) -> None:
        """Stop optional module-owned background work."""

    @abstractmethod
    async def handle_update(
        self, update: TelegramUpdate, context: BotContext
    ) -> None:
        """Handle one already-authenticated, idempotently claimed update."""


@dataclass(frozen=True, slots=True)
class BotDependencies:
    database: Database
    settings: Settings
    telegram: TelegramBotClient
    http: httpx.AsyncClient


BotFactory = Callable[[BotRuntimeConfig, BotDependencies], BaseBot]


class BotModuleRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, BotFactory] = {}
        self._sealed = False

    def register(self, *, name: str, factory: BotFactory) -> None:
        if self._sealed:
            raise InvalidBotModuleError("Module registry is already sealed.")
        if name in self._factories:
            raise InvalidBotModuleError(f"Duplicate bot module registration: {name}")
        self._factories[name] = factory

    def get(self, name: str) -> BotFactory:
        try:
            return self._factories[name]
        except KeyError as error:
            raise InvalidBotModuleError(
                f"No registered module factory for {name}"
            ) from error

    def seal(self) -> None:
        self._sealed = True

    @property
    def factories(self) -> Mapping[str, BotFactory]:
        return MappingProxyType(self._factories)

    def __len__(self) -> int:
        return len(self._factories)


@dataclass(slots=True)
class RuntimeBot:
    config: BotRuntimeConfig
    bot: BaseBot | None
    telegram: TelegramBotClient
    token: SecretStr
    secret_token: SecretStr
    healthy: bool = True
    health_reason: str | None = None


class RuntimeBotRegistry:
    def __init__(self) -> None:
        self._bots: dict[str, RuntimeBot] = {}
        self._disabled: dict[str, BotDescriptor] = {}
        self._sealed = False

    def add(self, runtime: RuntimeBot) -> None:
        if self._sealed:
            raise RuntimeError("Runtime registry is sealed")
        if runtime.config.name in self._bots or runtime.config.name in self._disabled:
            raise InvalidBotModuleError(
                f"Duplicate runtime bot: {runtime.config.name}"
            )
        self._bots[runtime.config.name] = runtime

    def add_disabled(self, descriptor: BotDescriptor) -> None:
        if self._sealed:
            raise RuntimeError("Runtime registry is sealed")
        self._disabled[descriptor.name] = descriptor

    def get(self, name: str) -> RuntimeBot:
        if name in self._disabled:
            raise BotDisabledError
        try:
            runtime = self._bots[name]
        except KeyError as error:
            raise BotNotFoundError from error
        if runtime.bot is None:
            raise BotUnavailableError
        return runtime

    def mark_unhealthy(self, name: str, reason: str) -> None:
        runtime = self._bots.get(name)
        if runtime is not None:
            runtime.healthy = False
            runtime.health_reason = reason

    def seal(self) -> None:
        self._sealed = True

    @property
    def bots(self) -> Mapping[str, RuntimeBot]:
        return MappingProxyType(self._bots)

    @property
    def enabled_count(self) -> int:
        return len(self._bots)

    @property
    def healthy_count(self) -> int:
        return sum(runtime.healthy for runtime in self._bots.values())

    @property
    def unhealthy_count(self) -> int:
        return self.enabled_count - self.healthy_count
