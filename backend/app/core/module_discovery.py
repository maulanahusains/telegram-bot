from __future__ import annotations

import importlib
import pkgutil
import re
from collections.abc import Callable
from types import ModuleType
from typing import cast

import app.modules
from app.core.logging import get_logger
from app.core.registry import BotModuleRegistry
from app.shared.exceptions import InvalidBotModuleError

MODULE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
logger = get_logger(__name__)


async def discover_modules(registry: BotModuleRegistry) -> None:
    package_path = app.modules.__path__
    discovered: list[str] = []
    for info in sorted(pkgutil.iter_modules(package_path), key=lambda item: item.name):
        if not info.ispkg:
            continue
        if MODULE_PATTERN.fullmatch(info.name) is None:
            raise InvalidBotModuleError(f"Invalid module package name: {info.name}")
        qualified_name = f"{app.modules.__name__}.{info.name}"
        module = importlib.import_module(qualified_name)
        _register_module(module, registry)
        discovered.append(info.name)
        await logger.ainfo("bot_module_discovered", module_name=info.name)
    registry.seal()
    await logger.ainfo("bot_module_discovery_complete", modules=discovered)


def _register_module(module: ModuleType, registry: BotModuleRegistry) -> None:
    register = getattr(module, "register", None)
    if not callable(register):
        raise InvalidBotModuleError(
            f"Trusted module {module.__name__} does not expose register(registry)"
        )
    cast(Callable[[BotModuleRegistry], None], register)(registry)

