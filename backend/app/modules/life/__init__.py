from app.core.registry import BotModuleRegistry
from app.modules.life.bot import create_life_bot


def register(registry: BotModuleRegistry) -> None:
    registry.register(name="life", factory=create_life_bot)
