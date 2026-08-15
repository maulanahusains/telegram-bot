from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.life.models import LifeDestinationCandidateModel, LifeNotificationDestinationModel, LifeNutritionGoalModel, LifeProfileModel, LifeReminderModel, LifeReminderOccurrenceModel
from app.platform.bots.models import TelegramBotModel
from app.platform.users.models import TelegramChatModel


class LifeRepository:
    async def profile(self, session: AsyncSession, owner_user_id: int, *, locked: bool = False) -> LifeProfileModel | None:
        statement = select(LifeProfileModel).where(LifeProfileModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def goals(self, session: AsyncSession, owner_user_id: int) -> list[LifeNutritionGoalModel]:
        values = await session.scalars(select(LifeNutritionGoalModel).where(LifeNutritionGoalModel.owner_user_id == owner_user_id).order_by(LifeNutritionGoalModel.effective_from.desc(), LifeNutritionGoalModel.id.desc()))
        return list(values)

    async def candidates(self, session: AsyncSession, owner_user_id: int) -> list[tuple[LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel]]:
        rows = await session.execute(select(LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel).join(TelegramBotModel, TelegramBotModel.id == LifeDestinationCandidateModel.bot_id).join(TelegramChatModel, TelegramChatModel.id == LifeDestinationCandidateModel.telegram_chat_id).where(LifeDestinationCandidateModel.owner_user_id == owner_user_id, TelegramBotModel.module_name == "life", TelegramBotModel.enabled.is_(True)).order_by(LifeDestinationCandidateModel.last_seen_at.desc()))
        return list(rows.tuples())

    async def candidate(self, session: AsyncSession, owner_user_id: int, candidate_id: int) -> tuple[LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel] | None:
        rows = await session.execute(select(LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel).join(TelegramBotModel, TelegramBotModel.id == LifeDestinationCandidateModel.bot_id).join(TelegramChatModel, TelegramChatModel.id == LifeDestinationCandidateModel.telegram_chat_id).where(LifeDestinationCandidateModel.id == candidate_id, LifeDestinationCandidateModel.owner_user_id == owner_user_id, TelegramBotModel.module_name == "life", TelegramBotModel.enabled.is_(True)).with_for_update(of=LifeDestinationCandidateModel))
        return rows.tuples().one_or_none()

    async def destinations(self, session: AsyncSession, owner_user_id: int) -> list[tuple[LifeNotificationDestinationModel, TelegramBotModel, TelegramChatModel]]:
        rows = await session.execute(select(LifeNotificationDestinationModel, TelegramBotModel, TelegramChatModel).join(TelegramBotModel, TelegramBotModel.id == LifeNotificationDestinationModel.bot_id).join(TelegramChatModel, TelegramChatModel.id == LifeNotificationDestinationModel.telegram_chat_id).where(LifeNotificationDestinationModel.owner_user_id == owner_user_id).order_by(LifeNotificationDestinationModel.is_default.desc(), LifeNotificationDestinationModel.created_at))
        return list(rows.tuples())

    async def destination(self, session: AsyncSession, owner_user_id: int, destination_id: int) -> LifeNotificationDestinationModel | None:
        return await session.scalar(select(LifeNotificationDestinationModel).where(LifeNotificationDestinationModel.id == destination_id, LifeNotificationDestinationModel.owner_user_id == owner_user_id).with_for_update())

    async def destination_context(self, session: AsyncSession, model: LifeNotificationDestinationModel) -> tuple[TelegramBotModel, TelegramChatModel]:
        rows = await session.execute(select(TelegramBotModel, TelegramChatModel).join(TelegramChatModel, TelegramChatModel.id == model.telegram_chat_id).where(TelegramBotModel.id == model.bot_id))
        return rows.tuples().one()

    async def find_destination_for_chat(self, session: AsyncSession, *, owner_user_id: int, bot_id: int, telegram_chat_id: int) -> LifeNotificationDestinationModel | None:
        return await session.scalar(select(LifeNotificationDestinationModel).where(LifeNotificationDestinationModel.owner_user_id == owner_user_id, LifeNotificationDestinationModel.bot_id == bot_id, LifeNotificationDestinationModel.telegram_chat_id == telegram_chat_id).with_for_update())

    async def clear_default(self, session: AsyncSession, owner_user_id: int) -> None:
        await session.execute(update(LifeNotificationDestinationModel).where(LifeNotificationDestinationModel.owner_user_id == owner_user_id, LifeNotificationDestinationModel.is_default.is_(True)).values(is_default=False))

    async def record_candidate(self, session: AsyncSession, *, owner_user_id: int, bot_id: int, telegram_chat_id: int, now: datetime) -> None:
        await session.execute(insert(LifeDestinationCandidateModel).values(owner_user_id=owner_user_id, bot_id=bot_id, telegram_chat_id=telegram_chat_id, last_seen_at=now).on_conflict_do_update(constraint="uq_life_destination_candidate_owner_bot_chat", set_={"last_seen_at": now}))

    async def reminders(self, session: AsyncSession, owner_user_id: int) -> list[LifeReminderModel]:
        values = await session.scalars(select(LifeReminderModel).where(LifeReminderModel.owner_user_id == owner_user_id).order_by(LifeReminderModel.next_run_at.is_(None), LifeReminderModel.next_run_at, LifeReminderModel.id))
        return list(values)

    async def reminder(self, session: AsyncSession, owner_user_id: int, reminder_id: int, *, locked: bool = False) -> LifeReminderModel | None:
        statement = select(LifeReminderModel).where(LifeReminderModel.id == reminder_id, LifeReminderModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def occurrences(self, session: AsyncSession, owner_user_id: int, reminder_id: int, *, limit: int) -> list[LifeReminderOccurrenceModel]:
        values = await session.scalars(select(LifeReminderOccurrenceModel).join(LifeReminderModel, LifeReminderModel.id == LifeReminderOccurrenceModel.reminder_id).where(LifeReminderModel.id == reminder_id, LifeReminderModel.owner_user_id == owner_user_id).order_by(LifeReminderOccurrenceModel.scheduled_for.desc()).limit(limit))
        return list(values)

    async def due_reminders(self, session: AsyncSession, *, bot_id: int, now: datetime, limit: int) -> list[LifeReminderModel]:
        values = await session.scalars(select(LifeReminderModel).join(LifeNotificationDestinationModel, LifeNotificationDestinationModel.id == LifeReminderModel.destination_id).where(LifeReminderModel.enabled.is_(True), LifeReminderModel.next_run_at.is_not(None), LifeReminderModel.next_run_at <= now, LifeNotificationDestinationModel.bot_id == bot_id, LifeNotificationDestinationModel.enabled.is_(True)).order_by(LifeReminderModel.next_run_at, LifeReminderModel.id).with_for_update(skip_locked=True).limit(limit))
        return list(values)

    async def insert_occurrence(self, session: AsyncSession, *, reminder_id: int, scheduled_for: datetime, status: str, now: datetime) -> None:
        await session.execute(insert(LifeReminderOccurrenceModel).values(reminder_id=reminder_id, scheduled_for=scheduled_for, status=status, available_at=now).on_conflict_do_nothing(constraint="uq_life_occurrence_reminder_scheduled"))

    async def claim_occurrences(self, session: AsyncSession, *, bot_id: int, now: datetime, lease_expires_at: datetime, limit: int) -> list[tuple[LifeReminderOccurrenceModel, LifeReminderModel, LifeNotificationDestinationModel, TelegramChatModel]]:
        rows = await session.execute(select(LifeReminderOccurrenceModel, LifeReminderModel, LifeNotificationDestinationModel, TelegramChatModel).join(LifeReminderModel, LifeReminderModel.id == LifeReminderOccurrenceModel.reminder_id).join(LifeNotificationDestinationModel, LifeNotificationDestinationModel.id == LifeReminderModel.destination_id).join(TelegramChatModel, TelegramChatModel.id == LifeNotificationDestinationModel.telegram_chat_id).where(LifeNotificationDestinationModel.bot_id == bot_id, LifeNotificationDestinationModel.enabled.is_(True), or_((LifeReminderOccurrenceModel.status == "pending") & (LifeReminderOccurrenceModel.available_at <= now), (LifeReminderOccurrenceModel.status == "claimed") & (LifeReminderOccurrenceModel.lease_expires_at.is_not(None)) & (LifeReminderOccurrenceModel.lease_expires_at <= now)).order_by(LifeReminderOccurrenceModel.available_at, LifeReminderOccurrenceModel.id).with_for_update(skip_locked=True).limit(limit))
        return list(rows.tuples())
