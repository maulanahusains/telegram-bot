from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.life.models import LifeDestinationCandidateModel, LifeFoodModel, LifeGoalPreferenceModel, LifeGoalRecommendationModel, LifeGroceryItemModel, LifeGroceryListModel, LifeMealLogItemModel, LifeMealLogModel, LifeMealTemplateItemModel, LifeMealTemplateModel, LifeNotificationDestinationModel, LifeNutritionGoalModel, LifeProfileModel, LifeRecurringGroceryItemModel, LifeReminderModel, LifeReminderOccurrenceModel, LifeWeightLogModel, LifeWorkoutCompletionModel, LifeWorkoutScheduleModel
from app.platform.bots.models import TelegramBotModel
from app.platform.users.models import TelegramChatModel, TelegramUserModel


class LifeRepository:
    async def lock_owner(self, session: AsyncSession, owner_user_id: int) -> None:
        await session.scalar(
            select(TelegramUserModel.id)
            .where(TelegramUserModel.id == owner_user_id)
            .with_for_update()
        )

    async def profile(self, session: AsyncSession, owner_user_id: int, *, locked: bool = False) -> LifeProfileModel | None:
        statement = select(LifeProfileModel).where(LifeProfileModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def goals(self, session: AsyncSession, owner_user_id: int) -> list[LifeNutritionGoalModel]:
        values = await session.scalars(select(LifeNutritionGoalModel).where(LifeNutritionGoalModel.owner_user_id == owner_user_id).order_by(LifeNutritionGoalModel.effective_from.desc(), LifeNutritionGoalModel.id.desc()))
        return list(values)

    async def goal_preference(self, session: AsyncSession, owner_user_id: int, *, locked: bool = False) -> LifeGoalPreferenceModel | None:
        statement = select(LifeGoalPreferenceModel).where(LifeGoalPreferenceModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def goal_preferences_for_evaluation(self, session: AsyncSession, *, limit: int) -> list[LifeGoalPreferenceModel]:
        values = await session.scalars(
            select(LifeGoalPreferenceModel)
            .order_by(LifeGoalPreferenceModel.last_evaluated_on.is_(None).desc(), LifeGoalPreferenceModel.last_evaluated_on, LifeGoalPreferenceModel.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(values)

    async def goal_recommendation(self, session: AsyncSession, owner_user_id: int, recommendation_id: int, *, locked: bool = False) -> LifeGoalRecommendationModel | None:
        statement = select(LifeGoalRecommendationModel).where(LifeGoalRecommendationModel.id == recommendation_id, LifeGoalRecommendationModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def goal_recommendations(self, session: AsyncSession, owner_user_id: int, *, limit: int) -> list[LifeGoalRecommendationModel]:
        values = await session.scalars(
            select(LifeGoalRecommendationModel)
            .where(LifeGoalRecommendationModel.owner_user_id == owner_user_id)
            .order_by(LifeGoalRecommendationModel.offered_at.desc(), LifeGoalRecommendationModel.id.desc())
            .limit(limit)
        )
        return list(values)

    async def pending_goal_recommendation(self, session: AsyncSession, owner_user_id: int, *, locked: bool = False) -> LifeGoalRecommendationModel | None:
        statement = select(LifeGoalRecommendationModel).where(LifeGoalRecommendationModel.owner_user_id == owner_user_id, LifeGoalRecommendationModel.status == "pending")
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def latest_decided_goal_recommendation(self, session: AsyncSession, owner_user_id: int) -> LifeGoalRecommendationModel | None:
        return await session.scalar(
            select(LifeGoalRecommendationModel)
            .where(
                LifeGoalRecommendationModel.owner_user_id == owner_user_id,
                LifeGoalRecommendationModel.status.in_(["applied", "dismissed"]),
                LifeGoalRecommendationModel.decided_at.is_not(None),
            )
            .order_by(LifeGoalRecommendationModel.decided_at.desc(), LifeGoalRecommendationModel.id.desc())
            .limit(1)
        )

    async def goal_for_effective_date(self, session: AsyncSession, owner_user_id: int, effective_from, *, locked: bool = False) -> LifeNutritionGoalModel | None:
        statement = select(LifeNutritionGoalModel).where(LifeNutritionGoalModel.owner_user_id == owner_user_id, LifeNutritionGoalModel.effective_from == effective_from)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def goal_recommendation_reminder(self, session: AsyncSession, recommendation_id: int, *, locked: bool = False) -> LifeReminderModel | None:
        statement = select(LifeReminderModel).where(LifeReminderModel.goal_recommendation_id == recommendation_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def candidates(self, session: AsyncSession, owner_user_id: int) -> list[tuple[LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel]]:
        rows = await session.execute(select(LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel).join(TelegramBotModel, TelegramBotModel.id == LifeDestinationCandidateModel.bot_id).join(TelegramChatModel, TelegramChatModel.id == LifeDestinationCandidateModel.telegram_chat_id).where(LifeDestinationCandidateModel.owner_user_id == owner_user_id, TelegramBotModel.module_name == "life", TelegramBotModel.enabled.is_(True)).order_by(LifeDestinationCandidateModel.last_seen_at.desc()))
        return list(rows.tuples())

    async def candidate(self, session: AsyncSession, owner_user_id: int, candidate_id: int) -> tuple[LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel] | None:
        rows = await session.execute(select(LifeDestinationCandidateModel, TelegramBotModel, TelegramChatModel).join(TelegramBotModel, TelegramBotModel.id == LifeDestinationCandidateModel.bot_id).join(TelegramChatModel, TelegramChatModel.id == LifeDestinationCandidateModel.telegram_chat_id).where(LifeDestinationCandidateModel.id == candidate_id, LifeDestinationCandidateModel.owner_user_id == owner_user_id, TelegramBotModel.module_name == "life", TelegramBotModel.enabled.is_(True)).with_for_update(of=LifeDestinationCandidateModel))
        return rows.tuples().one_or_none()

    async def destinations(self, session: AsyncSession, owner_user_id: int) -> list[tuple[LifeNotificationDestinationModel, TelegramBotModel, TelegramChatModel]]:
        rows = await session.execute(select(LifeNotificationDestinationModel, TelegramBotModel, TelegramChatModel).join(TelegramBotModel, TelegramBotModel.id == LifeNotificationDestinationModel.bot_id).join(TelegramChatModel, TelegramChatModel.id == LifeNotificationDestinationModel.telegram_chat_id).where(LifeNotificationDestinationModel.owner_user_id == owner_user_id).order_by(LifeNotificationDestinationModel.is_default.desc(), LifeNotificationDestinationModel.created_at))
        return list(rows.tuples())

    async def notification_destination_for_bot(self, session: AsyncSession, owner_user_id: int, bot_id: int) -> tuple[LifeNotificationDestinationModel, TelegramChatModel] | None:
        rows = await session.execute(
            select(LifeNotificationDestinationModel, TelegramChatModel)
            .join(TelegramChatModel, TelegramChatModel.id == LifeNotificationDestinationModel.telegram_chat_id)
            .where(
                LifeNotificationDestinationModel.owner_user_id == owner_user_id,
                LifeNotificationDestinationModel.bot_id == bot_id,
                LifeNotificationDestinationModel.enabled.is_(True),
                LifeNotificationDestinationModel.verified_at.is_not(None),
            )
            .order_by(
                LifeNotificationDestinationModel.is_default.desc(),
                LifeNotificationDestinationModel.created_at,
                LifeNotificationDestinationModel.id,
            )
            .with_for_update()
            .limit(1)
        )
        return rows.tuples().one_or_none()

    async def private_notification_destination_for_bot(self, session: AsyncSession, owner_user_id: int, bot_id: int) -> tuple[LifeNotificationDestinationModel, TelegramChatModel] | None:
        rows = await session.execute(
            select(LifeNotificationDestinationModel, TelegramChatModel)
            .join(TelegramChatModel, TelegramChatModel.id == LifeNotificationDestinationModel.telegram_chat_id)
            .where(
                LifeNotificationDestinationModel.owner_user_id == owner_user_id,
                LifeNotificationDestinationModel.bot_id == bot_id,
                LifeNotificationDestinationModel.kind == "private",
                TelegramChatModel.type == "private",
                LifeNotificationDestinationModel.enabled.is_(True),
                LifeNotificationDestinationModel.verified_at.is_not(None),
            )
            .order_by(
                LifeNotificationDestinationModel.is_default.desc(),
                LifeNotificationDestinationModel.created_at,
                LifeNotificationDestinationModel.id,
            )
            .with_for_update()
            .limit(1)
        )
        return rows.tuples().one_or_none()

    async def destination(self, session: AsyncSession, owner_user_id: int, destination_id: int) -> LifeNotificationDestinationModel | None:
        return await session.scalar(select(LifeNotificationDestinationModel).where(LifeNotificationDestinationModel.id == destination_id, LifeNotificationDestinationModel.owner_user_id == owner_user_id).with_for_update())

    async def destination_context(self, session: AsyncSession, model: LifeNotificationDestinationModel) -> tuple[TelegramBotModel, TelegramChatModel]:
        rows = await session.execute(select(TelegramBotModel, TelegramChatModel).join(TelegramChatModel, TelegramChatModel.id == model.telegram_chat_id).where(TelegramBotModel.id == model.bot_id))
        return rows.tuples().one()

    async def find_destination_for_chat(self, session: AsyncSession, *, owner_user_id: int, bot_id: int, telegram_chat_id: int) -> LifeNotificationDestinationModel | None:
        return await session.scalar(select(LifeNotificationDestinationModel).where(LifeNotificationDestinationModel.owner_user_id == owner_user_id, LifeNotificationDestinationModel.bot_id == bot_id, LifeNotificationDestinationModel.telegram_chat_id == telegram_chat_id).with_for_update())

    async def clear_default(self, session: AsyncSession, owner_user_id: int) -> None:
        await session.execute(update(LifeNotificationDestinationModel).where(LifeNotificationDestinationModel.owner_user_id == owner_user_id, LifeNotificationDestinationModel.is_default.is_(True)).values(is_default=False))

    async def record_candidate(
        self,
        session: AsyncSession,
        *,
        owner_user_id: int,
        bot_id: int,
        telegram_chat_external_id: int,
        now: datetime,
    ) -> None:
        """Record webhook evidence using the internal ``telegram_chats.id`` FK.

        ``UserContext.chat_id`` intentionally contains Telegram's public chat ID,
        while Life destination/candidate tables reference the platform chat row's
        internal primary key.  Resolve that row here instead of persisting the
        external value into the FK column.
        """
        telegram_chat_id = await session.scalar(
            select(TelegramChatModel.id).where(
                TelegramChatModel.telegram_chat_id == telegram_chat_external_id
            )
        )
        if telegram_chat_id is None:
            raise RuntimeError("Telegram chat context was not persisted.")

        statement = insert(LifeDestinationCandidateModel).values(
            owner_user_id=owner_user_id,
            bot_id=bot_id,
            telegram_chat_id=telegram_chat_id,
            last_seen_at=now,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_life_destination_candidate_owner_bot_chat",
            set_={"last_seen_at": now},
        )
        await session.execute(statement)

    async def reminders(self, session: AsyncSession, owner_user_id: int) -> list[LifeReminderModel]:
        values = await session.scalars(select(LifeReminderModel).where(LifeReminderModel.owner_user_id == owner_user_id, LifeReminderModel.kind.not_in(["grocery", "goal_recommendation"])).order_by(LifeReminderModel.next_run_at.is_(None), LifeReminderModel.next_run_at, LifeReminderModel.id))
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
        statement = (
            select(
                LifeReminderOccurrenceModel,
                LifeReminderModel,
                LifeNotificationDestinationModel,
                TelegramChatModel,
            )
            .join(
                LifeReminderModel,
                LifeReminderModel.id == LifeReminderOccurrenceModel.reminder_id,
            )
            .join(
                LifeNotificationDestinationModel,
                LifeNotificationDestinationModel.id == LifeReminderModel.destination_id,
            )
            .join(
                TelegramChatModel,
                TelegramChatModel.id == LifeNotificationDestinationModel.telegram_chat_id,
            )
            .where(
                LifeNotificationDestinationModel.bot_id == bot_id,
                LifeNotificationDestinationModel.enabled.is_(True),
                or_(
                    (LifeReminderOccurrenceModel.status == "pending")
                    & (LifeReminderOccurrenceModel.available_at <= now),
                    (LifeReminderOccurrenceModel.status == "claimed")
                    & (LifeReminderOccurrenceModel.lease_expires_at.is_not(None))
                    & (LifeReminderOccurrenceModel.lease_expires_at <= now),
                ),
            )
            .order_by(
                LifeReminderOccurrenceModel.available_at,
                LifeReminderOccurrenceModel.id,
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        rows = await session.execute(statement)
        return list(rows.tuples())

    async def foods(self, session: AsyncSession, owner_user_id: int, *, include_inactive: bool = True) -> list[LifeFoodModel]:
        statement = select(LifeFoodModel).where(LifeFoodModel.owner_user_id == owner_user_id)
        if not include_inactive:
            statement = statement.where(LifeFoodModel.active.is_(True))
        values = await session.scalars(statement.order_by(LifeFoodModel.active.desc(), LifeFoodModel.name, LifeFoodModel.id))
        return list(values)

    async def food(self, session: AsyncSession, owner_user_id: int, food_id: int, *, locked: bool = False) -> LifeFoodModel | None:
        statement = select(LifeFoodModel).where(LifeFoodModel.id == food_id, LifeFoodModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def template(self, session: AsyncSession, owner_user_id: int, template_id: int, *, locked: bool = False) -> LifeMealTemplateModel | None:
        statement = select(LifeMealTemplateModel).where(LifeMealTemplateModel.id == template_id, LifeMealTemplateModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def templates(self, session: AsyncSession, owner_user_id: int) -> list[LifeMealTemplateModel]:
        values = await session.scalars(select(LifeMealTemplateModel).where(LifeMealTemplateModel.owner_user_id == owner_user_id).order_by(LifeMealTemplateModel.active.desc(), LifeMealTemplateModel.name, LifeMealTemplateModel.id))
        return list(values)

    async def template_items(self, session: AsyncSession, template_id: int) -> list[tuple[LifeMealTemplateItemModel, LifeFoodModel]]:
        rows = await session.execute(select(LifeMealTemplateItemModel, LifeFoodModel).join(LifeFoodModel, LifeFoodModel.id == LifeMealTemplateItemModel.food_id).where(LifeMealTemplateItemModel.template_id == template_id).order_by(LifeMealTemplateItemModel.position))
        return list(rows.tuples())

    async def replace_template_items(self, session: AsyncSession, template_id: int, items: list[tuple[LifeFoodModel, object]]) -> None:
        await session.execute(LifeMealTemplateItemModel.__table__.delete().where(LifeMealTemplateItemModel.template_id == template_id))
        for position, (food, quantity) in enumerate(items):
            session.add(LifeMealTemplateItemModel(template_id=template_id, food_id=food.id, quantity=quantity, position=position))

    async def meal_log(self, session: AsyncSession, owner_user_id: int, log_id: int, *, locked: bool = False) -> LifeMealLogModel | None:
        statement = select(LifeMealLogModel).where(LifeMealLogModel.id == log_id, LifeMealLogModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def meal_logs(self, session: AsyncSession, owner_user_id: int, start_date, end_date) -> list[LifeMealLogModel]:
        values = await session.scalars(select(LifeMealLogModel).where(LifeMealLogModel.owner_user_id == owner_user_id, LifeMealLogModel.local_date >= start_date, LifeMealLogModel.local_date <= end_date).order_by(LifeMealLogModel.consumed_at, LifeMealLogModel.id))
        return list(values)

    async def meal_log_items(self, session: AsyncSession, log_id: int) -> list[LifeMealLogItemModel]:
        values = await session.scalars(select(LifeMealLogItemModel).where(LifeMealLogItemModel.meal_log_id == log_id).order_by(LifeMealLogItemModel.position))
        return list(values)

    async def weight_logs(self, session: AsyncSession, owner_user_id: int, start_date, end_date) -> list[LifeWeightLogModel]:
        values = await session.scalars(select(LifeWeightLogModel).where(LifeWeightLogModel.owner_user_id == owner_user_id, LifeWeightLogModel.local_date >= start_date, LifeWeightLogModel.local_date <= end_date).order_by(LifeWeightLogModel.local_date, LifeWeightLogModel.id))
        return list(values)

    async def weight_log_for_date(self, session: AsyncSession, owner_user_id: int, local_date, *, locked: bool = False) -> LifeWeightLogModel | None:
        statement = select(LifeWeightLogModel).where(LifeWeightLogModel.owner_user_id == owner_user_id, LifeWeightLogModel.local_date == local_date)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def workout_schedule(self, session: AsyncSession, owner_user_id: int, schedule_id: int, *, locked: bool = False) -> LifeWorkoutScheduleModel | None:
        statement = select(LifeWorkoutScheduleModel).where(LifeWorkoutScheduleModel.id == schedule_id, LifeWorkoutScheduleModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def workout_schedules(self, session: AsyncSession, owner_user_id: int) -> list[LifeWorkoutScheduleModel]:
        values = await session.scalars(select(LifeWorkoutScheduleModel).where(LifeWorkoutScheduleModel.owner_user_id == owner_user_id).order_by(LifeWorkoutScheduleModel.enabled.desc(), LifeWorkoutScheduleModel.name, LifeWorkoutScheduleModel.id))
        return list(values)

    async def workout_for_reminder(self, session: AsyncSession, reminder_id: int) -> LifeWorkoutScheduleModel | None:
        return await session.scalar(select(LifeWorkoutScheduleModel).where(LifeWorkoutScheduleModel.reminder_id == reminder_id))

    async def workout_completion(self, session: AsyncSession, occurrence_id: int) -> LifeWorkoutCompletionModel | None:
        return await session.scalar(select(LifeWorkoutCompletionModel).where(LifeWorkoutCompletionModel.occurrence_id == occurrence_id))

    async def workout_completions(self, session: AsyncSession, owner_user_id: int, start, end) -> list[LifeWorkoutCompletionModel]:
        values = await session.scalars(select(LifeWorkoutCompletionModel).join(LifeWorkoutScheduleModel, LifeWorkoutScheduleModel.id == LifeWorkoutCompletionModel.workout_schedule_id).where(LifeWorkoutScheduleModel.owner_user_id == owner_user_id, LifeWorkoutCompletionModel.scheduled_for >= start, LifeWorkoutCompletionModel.scheduled_for < end).order_by(LifeWorkoutCompletionModel.scheduled_for))
        return list(values)

    async def grocery_lists(self, session: AsyncSession, owner_user_id: int) -> list[LifeGroceryListModel]:
        values = await session.scalars(select(LifeGroceryListModel).where(LifeGroceryListModel.owner_user_id == owner_user_id).order_by(LifeGroceryListModel.starts_on.desc(), LifeGroceryListModel.id.desc()).limit(100))
        return list(values)

    async def grocery_lists_for_automation(self, session: AsyncSession, *, limit: int) -> list[LifeGroceryListModel]:
        values = await session.scalars(
            select(LifeGroceryListModel)
            .where(LifeGroceryListModel.status == "active")
            .order_by(LifeGroceryListModel.ends_on, LifeGroceryListModel.id)
            .limit(limit)
        )
        return list(values)

    async def active_grocery_list(self, session: AsyncSession, owner_user_id: int, *, locked: bool = False) -> LifeGroceryListModel | None:
        statement = select(LifeGroceryListModel).where(LifeGroceryListModel.owner_user_id == owner_user_id, LifeGroceryListModel.status == "active")
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def grocery_list(self, session: AsyncSession, owner_user_id: int, list_id: int, *, locked: bool = False) -> LifeGroceryListModel | None:
        statement = select(LifeGroceryListModel).where(LifeGroceryListModel.id == list_id, LifeGroceryListModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def grocery_items(self, session: AsyncSession, list_id: int) -> list[LifeGroceryItemModel]:
        values = await session.scalars(select(LifeGroceryItemModel).where(LifeGroceryItemModel.list_id == list_id).order_by(LifeGroceryItemModel.position, LifeGroceryItemModel.id))
        return list(values)

    async def grocery_item(self, session: AsyncSession, owner_user_id: int, list_id: int, item_id: int, *, locked: bool = False) -> LifeGroceryItemModel | None:
        statement = select(LifeGroceryItemModel).join(LifeGroceryListModel, LifeGroceryListModel.id == LifeGroceryItemModel.list_id).where(LifeGroceryItemModel.id == item_id, LifeGroceryItemModel.list_id == list_id, LifeGroceryListModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)

    async def recurring_grocery_items(self, session: AsyncSession, owner_user_id: int) -> list[LifeRecurringGroceryItemModel]:
        values = await session.scalars(select(LifeRecurringGroceryItemModel).where(LifeRecurringGroceryItemModel.owner_user_id == owner_user_id).order_by(LifeRecurringGroceryItemModel.enabled.desc(), LifeRecurringGroceryItemModel.name, LifeRecurringGroceryItemModel.id))
        return list(values)

    async def recurring_grocery_item(self, session: AsyncSession, owner_user_id: int, item_id: int, *, locked: bool = False) -> LifeRecurringGroceryItemModel | None:
        statement = select(LifeRecurringGroceryItemModel).where(LifeRecurringGroceryItemModel.id == item_id, LifeRecurringGroceryItemModel.owner_user_id == owner_user_id)
        return await session.scalar(statement.with_for_update() if locked else statement)
