from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.core.config import Settings
from app.core.database import Database
from app.platform.updates.repositories import ClaimResult, UpdateRepository
from app.shared.types import TelegramUpdate
from app.shared.utils import safe_error_summary, utc_now


@dataclass(frozen=True, slots=True)
class UpdateClaim:
    row_id: int
    result: ClaimResult
    attempts: int


class UpdateService:
    def __init__(
        self, database: Database, repository: UpdateRepository, settings: Settings
    ) -> None:
        self._database = database
        self._repository = repository
        self._settings = settings

    async def claim(self, bot_id: int, update: TelegramUpdate) -> UpdateClaim:
        user = update.effective_user()
        chat = update.effective_chat()
        now = utc_now()
        async with self._database.transaction() as session:
            model, result = await self._repository.claim(
                session,
                bot_id=bot_id,
                update_id=update.update_id,
                telegram_user_id=user.id if user else None,
                chat_id=chat.id if chat else None,
                update_type=update.update_type(),
                now=now,
                lease_expires_at=now
                + timedelta(seconds=self._settings.update_lease_seconds),
                max_attempts=self._settings.update_max_attempts,
            )
            await session.flush()
            return UpdateClaim(model.id, result, model.attempts)

    async def processed(self, claim: UpdateClaim) -> None:
        async with self._database.transaction() as session:
            await self._repository.mark_processed(session, claim.row_id)

    async def failed(self, claim: UpdateClaim, error: BaseException) -> bool:
        async with self._database.transaction() as session:
            await self._repository.mark_failed(
                session, claim.row_id, safe_error_summary(error)
            )
        return claim.attempts >= self._settings.update_max_attempts
