from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.updates.models import TelegramUpdateModel, UpdateStatus


class ClaimResult(StrEnum):
    CLAIMED = "claimed"
    DUPLICATE = "duplicate"
    IN_FLIGHT = "in_flight"
    EXHAUSTED = "exhausted"


class UpdateRepository:
    async def claim(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        update_id: int,
        telegram_user_id: int | None,
        chat_id: int | None,
        update_type: str,
        now: datetime,
        lease_expires_at: datetime,
        max_attempts: int,
    ) -> tuple[TelegramUpdateModel, ClaimResult]:
        created = await session.scalar(
            insert(TelegramUpdateModel)
            .values(
                bot_id=bot_id,
                update_id=update_id,
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                update_type=update_type,
                status=UpdateStatus.PROCESSING,
                attempts=1,
                lease_expires_at=lease_expires_at,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    TelegramUpdateModel.bot_id,
                    TelegramUpdateModel.update_id,
                ]
            )
            .returning(TelegramUpdateModel)
        )
        if created is not None:
            return created, ClaimResult.CLAIMED

        model = await session.scalar(
            select(TelegramUpdateModel)
            .where(
                TelegramUpdateModel.bot_id == bot_id,
                TelegramUpdateModel.update_id == update_id,
            )
            .with_for_update()
        )
        if model is None:
            raise RuntimeError("Update claim did not return a row")
        if model.status is UpdateStatus.PROCESSED:
            return model, ClaimResult.DUPLICATE
        if (
            model.status is UpdateStatus.PROCESSING
            and model.lease_expires_at is not None
            and model.lease_expires_at > now
        ):
            return model, ClaimResult.IN_FLIGHT
        if model.attempts >= max_attempts:
            return model, ClaimResult.EXHAUSTED

        model.status = UpdateStatus.PROCESSING
        model.attempts += 1
        model.lease_expires_at = lease_expires_at
        model.error_message = None
        return model, ClaimResult.CLAIMED

    async def mark_processed(
        self, session: AsyncSession, update_row_id: int
    ) -> None:
        await session.execute(
            update(TelegramUpdateModel)
            .where(TelegramUpdateModel.id == update_row_id)
            .values(
                status=UpdateStatus.PROCESSED,
                processed_at=func.now(),
                lease_expires_at=None,
                error_message=None,
            )
        )

    async def mark_failed(
        self, session: AsyncSession, update_row_id: int, error_message: str
    ) -> None:
        await session.execute(
            update(TelegramUpdateModel)
            .where(TelegramUpdateModel.id == update_row_id)
            .values(
                status=UpdateStatus.FAILED,
                lease_expires_at=None,
                error_message=error_message,
            )
        )

