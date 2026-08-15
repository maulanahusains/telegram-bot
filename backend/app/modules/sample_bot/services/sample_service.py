from __future__ import annotations

from app.core.database import Database
from app.modules.sample_bot.repositories.sample_repository import SampleRepository
from app.platform.users.services import UserStateService


class SampleService:
    def __init__(
        self,
        database: Database,
        repository: SampleRepository,
        state_service: UserStateService,
    ) -> None:
        self._database = database
        self._repository = repository
        self._state_service = state_service

    async def record_command(self, bot_user_id: int) -> None:
        async with self._database.transaction() as session:
            await self._repository.touch_profile(session, bot_user_id)

    async def increment_counter(self, bot_user_id: int, update_id: int) -> int:
        def increment(data: dict[str, object]) -> dict[str, object]:
            if data.get("last_counter_update_id") == update_id:
                return data
            current = data.get("counter", 0)
            value = current if isinstance(current, int) and not isinstance(current, bool) else 0
            data["counter"] = value + 1
            data["last_counter_update_id"] = update_id
            return data

        state = await self._state_service.update_state(bot_user_id, increment)
        counter = state.data.get("counter", 0)
        return counter if isinstance(counter, int) else 0
