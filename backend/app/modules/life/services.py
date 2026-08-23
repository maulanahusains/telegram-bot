from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.core.config import Settings
from app.core.logging import get_logger
from app.core.telegram_client import SentMessage
from app.modules.life.models import LifeFoodModel, LifeGoalPreferenceModel, LifeGoalRecommendationModel, LifeGroceryItemModel, LifeGroceryListModel, LifeMealLogItemModel, LifeMealLogModel, LifeMealTemplateModel, LifeNotificationDestinationModel, LifeNutritionGoalModel, LifeProfileModel, LifeRecurringGroceryItemModel, LifeReminderModel, LifeReminderOccurrenceModel, LifeWeightLogModel, LifeWorkoutCompletionModel, LifeWorkoutScheduleModel
from app.modules.life.repositories import LifeRepository
from app.modules.life.schemas import DestinationActivationInput, DestinationCandidateValue, DestinationPatch, FoodInput, FoodPatch, FoodValue, GoalPreferenceInput, GoalPreferenceValue, GoalRecommendationValue, GroceryItemInput, GroceryItemPatch, GroceryItemValue, GroceryListInput, GroceryListPatch, GroceryListState, GroceryListValue, LifeProfileInput, LifeProfileValue, MealLogInput, MealLogItemValue, MealLogValue, MealTemplateInput, MealTemplateItemValue, MealTemplatePatch, MealTemplateValue, NotificationDestinationValue, NutritionGoalInput, NutritionGoalValue, ProgressDayValue, ProgressValue, RecurrenceRule, RecurringGroceryItemInput, RecurringGroceryItemPatch, RecurringGroceryItemValue, ReminderInput, ReminderOccurrenceValue, ReminderPatch, ReminderValue, TodayValue, WeightLogInput, WeightLogValue, WorkoutCompletionInput, WorkoutCompletionValue, WorkoutScheduleInput, WorkoutSchedulePatch, WorkoutScheduleValue
from app.shared.exceptions import LifeForbiddenError, LifeNotFoundError, LifeValidationError, TelegramAPIError
from app.shared.types import UserContext
from app.shared.utils import utc_now

logger = get_logger(__name__)

_WEEKDAY_NUMBERS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass(frozen=True, slots=True)
class ReminderDeliveryClaim:
    occurrence_id: int
    claim_token: str
    destination_id: int
    telegram_chat_id: int
    chat_type: str
    title: str
    kind: str
    scheduled_for: datetime
    notes: str | None = None
    goal_recommendation_id: int | None = None
    goal_recommendation_current_kcal: int | None = None
    goal_recommendation_recommended_kcal: int | None = None


@dataclass(frozen=True, slots=True)
class GoalRecommendationAction:
    status: str
    message: str


class LifeService:
    def __init__(self, database: Database, settings: Settings) -> None:
        self._database = database
        self._settings = settings
        self._repository = LifeRepository()

    async def profile(self, owner_user_id: int) -> LifeProfileValue | None:
        async with self._database.session() as session:
            model = await self._repository.profile(session, owner_user_id)
            return self._profile_value(model) if model else None

    async def put_profile(self, owner_user_id: int, data: LifeProfileInput) -> LifeProfileValue:
        self._validate_timezone(data.timezone)
        async with self._database.transaction() as session:
            model = await self._repository.profile(session, owner_user_id, locked=True)
            if model is None:
                model = LifeProfileModel(owner_user_id=owner_user_id, **data.model_dump())
                session.add(model)
                await session.flush()
            else:
                for field, value in data.model_dump().items():
                    setattr(model, field, value)
            return self._profile_value(model)

    async def goals(self, owner_user_id: int) -> list[NutritionGoalValue]:
        async with self._database.session() as session:
            return [self._goal_value(item) for item in await self._repository.goals(session, owner_user_id)]

    async def create_goal(self, owner_user_id: int, data: NutritionGoalInput) -> NutritionGoalValue:
        async with self._database.transaction() as session:
            if any(goal.effective_from == data.effective_from for goal in await self._repository.goals(session, owner_user_id)):
                raise LifeValidationError("A goal already exists for this effective date.")
            model = LifeNutritionGoalModel(owner_user_id=owner_user_id, **data.model_dump())
            session.add(model)
            await session.flush()
            return self._goal_value(model)

    async def goal_preference(self, owner_user_id: int) -> GoalPreferenceValue | None:
        async with self._database.session() as session:
            model = await self._repository.goal_preference(session, owner_user_id)
            return self._goal_preference_value(model) if model else None

    async def put_goal_preference(self, owner_user_id: int, data: GoalPreferenceInput) -> GoalPreferenceValue:
        async with self._database.transaction() as session:
            model = await self._repository.goal_preference(session, owner_user_id, locked=True)
            if model is None:
                model = LifeGoalPreferenceModel(owner_user_id=owner_user_id, **data.model_dump())
                session.add(model)
                await session.flush()
            else:
                changed = model.goal_direction != data.goal_direction or model.desired_weekly_change_kg != data.desired_weekly_change_kg
                model.goal_direction = data.goal_direction
                model.desired_weekly_change_kg = data.desired_weekly_change_kg
                if changed:
                    pending = await self._repository.pending_goal_recommendation(session, owner_user_id, locked=True)
                    if pending is not None:
                        pending.status = "superseded"
                        pending.decided_at = utc_now()
                        reminder = await self._repository.goal_recommendation_reminder(session, pending.id, locked=True)
                        if reminder is not None:
                            reminder.enabled = False
                            reminder.next_run_at = None
            return self._goal_preference_value(model)

    async def goal_recommendations(self, owner_user_id: int) -> list[GoalRecommendationValue]:
        async with self._database.session() as session:
            models = await self._repository.goal_recommendations(session, owner_user_id, limit=50)
            return [self._goal_recommendation_value(model) for model in models]

    async def transition_goal_recommendation(self, owner_user_id: int, recommendation_id: int, action: str) -> GoalRecommendationAction:
        if action not in {"apply", "dismiss"}:
            raise LifeValidationError("Unsupported goal recommendation action.")
        async with self._database.transaction() as session:
            recommendation = await self._repository.goal_recommendation(session, owner_user_id, recommendation_id, locked=True)
            if recommendation is None:
                raise LifeNotFoundError
            now = utc_now()
            if recommendation.status != "pending":
                return GoalRecommendationAction(recommendation.status, "Pilihan rekomendasi ini sudah diproses.")
            if now >= recommendation.expires_at:
                recommendation.status = "expired"
                recommendation.decided_at = now
                return GoalRecommendationAction("expired", "Rekomendasi ini sudah kedaluwarsa.")
            if action == "dismiss":
                recommendation.status = "dismissed"
                recommendation.decided_at = now
                return GoalRecommendationAction("dismissed", "Oke, target kalori tidak diubah.")

            timezone = await self._owner_timezone(session, owner_user_id)
            local_date = now.astimezone(ZoneInfo(timezone)).date()
            current_goal = await self._goal_for_date(session, owner_user_id, local_date)
            if current_goal is None or current_goal.id != recommendation.current_goal_id or current_goal.calorie_target_kcal != recommendation.current_calorie_target_kcal:
                recommendation.status = "superseded"
                recommendation.decided_at = now
                return GoalRecommendationAction("superseded", "Target saat ini sudah berubah, jadi rekomendasi ini tidak diterapkan.")
            if await self._repository.goal_for_effective_date(session, owner_user_id, local_date, locked=True) is not None:
                recommendation.status = "superseded"
                recommendation.decided_at = now
                return GoalRecommendationAction("superseded", "Sudah ada target manual untuk hari ini, jadi rekomendasi ini tidak diterapkan.")

            model = LifeNutritionGoalModel(
                owner_user_id=owner_user_id,
                calorie_target_kcal=recommendation.recommended_calorie_target_kcal,
                protein_min_g=current_goal.protein_min_g,
                protein_max_g=current_goal.protein_max_g,
                effective_from=local_date,
            )
            session.add(model)
            recommendation.status = "applied"
            recommendation.decided_at = now
            return GoalRecommendationAction("applied", f"Target baru {model.calorie_target_kcal:,} kcal/hari diterapkan mulai {local_date.isoformat()}.")

    async def evaluate_goal_recommendations(self, bot_id: int) -> int:
        if not self._settings.life_goal_recommendations_enabled:
            return 0
        now = utc_now()
        created = 0
        async with self._database.transaction() as session:
            preferences = await self._repository.goal_preferences_for_evaluation(
                session,
                limit=self._settings.life_reminder_executor_batch_size,
            )
            for preference in preferences:
                profile = await self._repository.profile(session, preference.owner_user_id)
                if profile is None:
                    continue
                self._validate_timezone(profile.timezone)
                local_today = now.astimezone(ZoneInfo(profile.timezone)).date()
                pending = await self._repository.pending_goal_recommendation(session, preference.owner_user_id, locked=True)
                if pending is not None:
                    if now >= pending.expires_at:
                        pending.status = "expired"
                        pending.decided_at = now
                    else:
                        await self._schedule_goal_recommendation_delivery(session, pending, profile.timezone, bot_id, now)
                        continue
                if preference.last_evaluated_on is not None and local_today - preference.last_evaluated_on < timedelta(days=self._settings.life_goal_recommendation_cadence_days):
                    continue
                preference.last_evaluated_on = local_today

                latest = await self._repository.latest_decided_goal_recommendation(session, preference.owner_user_id)
                if latest is not None and latest.decided_at is not None and now - latest.decided_at < timedelta(days=self._settings.life_goal_recommendation_cooldown_days):
                    continue
                current_goal = await self._goal_for_date(session, preference.owner_user_id, local_today)
                if current_goal is None:
                    continue
                logs = await self._repository.weight_logs(
                    session,
                    preference.owner_user_id,
                    local_today - timedelta(days=self._settings.life_goal_recommendation_window_days - 1),
                    local_today,
                )
                if len(logs) < self._settings.life_goal_recommendation_min_observations:
                    continue
                observed_dates = sorted({log.local_date for log in logs})
                if any((right - left).days > self._settings.life_goal_recommendation_max_gap_days for left, right in zip(observed_dates, observed_dates[1:])):
                    continue
                trend = self._weight_trend(logs)
                desired = preference.desired_weekly_change_kg
                if desired is None:
                    continue
                adjustment = self._calorie_adjustment(preference.goal_direction, trend, desired)
                if adjustment == 0:
                    continue
                recommended = current_goal.calorie_target_kcal + adjustment
                if not 0 < recommended <= 20_000:
                    continue

                window_start = min(log.local_date for log in logs)
                window_end = max(log.local_date for log in logs)
                recommendation = LifeGoalRecommendationModel(
                    owner_user_id=preference.owner_user_id,
                    current_goal_id=current_goal.id,
                    current_calorie_target_kcal=current_goal.calorie_target_kcal,
                    recommended_calorie_target_kcal=recommended,
                    goal_direction=preference.goal_direction,
                    desired_weekly_change_kg=preference.desired_weekly_change_kg,
                    window_start=window_start,
                    window_end=window_end,
                    observation_count=len(logs),
                    trend_kg_per_week=trend,
                    rule_version="weight-trend-v1",
                    rule_snapshot={
                        "window_days": self._settings.life_goal_recommendation_window_days,
                        "min_observations": self._settings.life_goal_recommendation_min_observations,
                        "max_gap_days": self._settings.life_goal_recommendation_max_gap_days,
                        "tolerance_kg_per_week": str(self._settings.life_goal_recommendation_tolerance_kg_per_week),
                        "delta_kcal": self._settings.life_goal_recommendation_delta_kcal,
                        "desired_weekly_change_kg": str(desired),
                        "observed_dates": [item.isoformat() for item in observed_dates],
                    },
                    offered_at=now,
                    expires_at=now + timedelta(days=self._settings.life_goal_recommendation_expiry_days),
                )
                session.add(recommendation)
                await session.flush()
                await self._schedule_goal_recommendation_delivery(session, recommendation, profile.timezone, bot_id, now)
                created += 1
        return created

    async def _schedule_goal_recommendation_delivery(self, session: AsyncSession, recommendation: LifeGoalRecommendationModel, timezone: str, bot_id: int, now: datetime) -> None:
        if await self._repository.goal_recommendation_reminder(session, recommendation.id) is not None:
            return
        destination_context = await self._repository.private_notification_destination_for_bot(session, recommendation.owner_user_id, bot_id)
        if destination_context is None:
            return
        destination, _ = destination_context
        grace_seconds = max(60, int((recommendation.expires_at - now).total_seconds()))
        session.add(
            LifeReminderModel(
                owner_user_id=recommendation.owner_user_id,
                destination_id=destination.id,
                title="Life calorie check-in",
                notes=self._goal_recommendation_notes(recommendation),
                kind="goal_recommendation",
                schedule_type="one_time",
                scheduled_at=now,
                timezone=timezone,
                recurrence=None,
                enabled=True,
                one_time_grace_seconds=grace_seconds,
                goal_recommendation_id=recommendation.id,
                next_run_at=now,
            )
        )

    def _goal_recommendation_notes(self, recommendation: LifeGoalRecommendationModel) -> str:
        trend = recommendation.trend_kg_per_week
        if trend > 0:
            trend_text = f"naik {trend:.2f} kg/minggu"
        elif trend < 0:
            trend_text = f"turun {abs(trend):.2f} kg/minggu"
        else:
            trend_text = "stabil"
        return (
            f"Dalam {recommendation.observation_count} observasi, tren beratmu {trend_text}.\n"
            f"Target sekarang: {recommendation.current_calorie_target_kcal:,} kcal/hari.\n"
            f"Rekomendasi: {recommendation.recommended_calorie_target_kcal:,} kcal/hari."
        )

    def _calorie_adjustment(self, direction: str, trend: Decimal, desired: Decimal) -> int:
        tolerance = self._settings.life_goal_recommendation_tolerance_kg_per_week
        if direction == "lose_weight":
            if trend > desired + tolerance:
                return -self._settings.life_goal_recommendation_delta_kcal
            if trend < desired - tolerance:
                return self._settings.life_goal_recommendation_delta_kcal
        elif direction == "maintain_weight":
            if trend > tolerance:
                return -self._settings.life_goal_recommendation_delta_kcal
            if trend < -tolerance:
                return self._settings.life_goal_recommendation_delta_kcal
        elif direction == "gain_weight":
            if trend < desired - tolerance:
                return self._settings.life_goal_recommendation_delta_kcal
            if trend > desired + tolerance:
                return -self._settings.life_goal_recommendation_delta_kcal
        return 0

    @staticmethod
    def _weight_trend(logs: list[LifeWeightLogModel]) -> Decimal:
        if len(logs) < 2:
            return Decimal("0.0000")
        origin = min(log.local_date for log in logs)
        points = [(Decimal((log.local_date - origin).days), log.weight_kg) for log in logs]
        x_mean = sum((point[0] for point in points), start=Decimal("0")) / len(points)
        y_mean = sum((point[1] for point in points), start=Decimal("0")) / len(points)
        numerator = sum(((x - x_mean) * (y - y_mean) for x, y in points), start=Decimal("0"))
        denominator = sum(((x - x_mean) ** 2 for x, _ in points), start=Decimal("0"))
        if denominator == 0:
            return Decimal("0.0000")
        return (numerator / denominator * Decimal("7")).quantize(Decimal("0.0001"))

    async def record_destination_candidate(self, context: UserContext) -> None:
        if context.chat_type not in {"private", "group", "supergroup"}:
            return
        async with self._database.transaction() as session:
            await self._repository.record_candidate(
                session,
                owner_user_id=context.internal_user_id,
                bot_id=context.bot_id,
                telegram_chat_external_id=context.chat_id,
                now=utc_now(),
            )

    async def candidates(self, owner_user_id: int) -> list[DestinationCandidateValue]:
        async with self._database.session() as session:
            return [self._candidate_value(*row) for row in await self._repository.candidates(session, owner_user_id)]

    async def destinations(self, owner_user_id: int) -> list[NotificationDestinationValue]:
        async with self._database.session() as session:
            return [self._destination_value(*row) for row in await self._repository.destinations(session, owner_user_id)]

    async def activate_candidate(self, owner_user_id: int, candidate_id: int, data: DestinationActivationInput) -> NotificationDestinationValue:
        async with self._database.transaction() as session:
            candidate = await self._repository.candidate(session, owner_user_id, candidate_id)
            if candidate is None:
                raise LifeNotFoundError
            candidate_model, bot, chat = candidate
            if chat.type not in {"private", "group", "supergroup"}:
                raise LifeValidationError("This chat type cannot be a notification destination.")
            destination = await self._repository.find_destination_for_chat(session, owner_user_id=owner_user_id, bot_id=candidate_model.bot_id, telegram_chat_id=candidate_model.telegram_chat_id)
            make_default = data.make_default or not await self._has_default(session, owner_user_id)
            if make_default:
                await self._repository.clear_default(session, owner_user_id)
            if destination is None:
                destination = LifeNotificationDestinationModel(owner_user_id=owner_user_id, bot_id=candidate_model.bot_id, telegram_chat_id=candidate_model.telegram_chat_id, kind=chat.type, label=data.label, enabled=True, is_default=make_default, verified_at=utc_now())
                session.add(destination)
                await session.flush()
            else:
                destination.kind = chat.type
                destination.label = data.label
                destination.enabled = True
                destination.is_default = make_default
                destination.verified_at = utc_now()
                destination.disabled_reason = None
            return self._destination_value(destination, bot, chat)

    async def patch_destination(self, owner_user_id: int, destination_id: int, data: DestinationPatch) -> NotificationDestinationValue:
        async with self._database.transaction() as session:
            model = await self._repository.destination(session, owner_user_id, destination_id)
            if model is None:
                raise LifeNotFoundError
            if data.label is not None:
                model.label = data.label
            if data.enabled is not None:
                model.enabled = data.enabled
                if not data.enabled:
                    model.is_default = False
            if data.is_default:
                if not model.enabled:
                    raise LifeValidationError("A disabled destination cannot be default.")
                await self._repository.clear_default(session, owner_user_id)
                model.is_default = True
            bot, chat = await self._repository.destination_context(session, model)
            return self._destination_value(model, bot, chat)

    async def reminders(self, owner_user_id: int) -> list[ReminderValue]:
        async with self._database.session() as session:
            return [self._reminder_value(value) for value in await self._repository.reminders(session, owner_user_id)]

    async def create_reminder(self, owner_user_id: int, data: ReminderInput) -> ReminderValue:
        if data.kind == "goal_recommendation":
            raise LifeValidationError("Goal recommendation reminders are managed by Life.")
        async with self._database.transaction() as session:
            timezone = await self._resolve_reminder_timezone(session, owner_user_id, data.timezone)
            destination = await self._active_destination(session, owner_user_id, data.destination_id)
            scheduled_at, recurrence, next_run_at = self._schedule_values(data, timezone, utc_now())
            model = LifeReminderModel(owner_user_id=owner_user_id, destination_id=destination.id, title=data.title or "", notes=data.notes, kind=data.kind, schedule_type=data.schedule_type, scheduled_at=scheduled_at, timezone=timezone, recurrence=recurrence, enabled=data.enabled, next_run_at=next_run_at if data.enabled else None)
            session.add(model)
            await session.flush()
            if model.kind == "workout":
                session.add(LifeWorkoutScheduleModel(owner_user_id=owner_user_id, reminder_id=model.id, name=model.title, enabled=model.enabled))
            return self._reminder_value(model)

    async def patch_reminder(self, owner_user_id: int, reminder_id: int, patch: ReminderPatch) -> ReminderValue:
        if patch.kind == "goal_recommendation":
            raise LifeValidationError("Goal recommendation reminders are managed by Life.")
        async with self._database.transaction() as session:
            model = await self._repository.reminder(session, owner_user_id, reminder_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            values = self._reminder_input_values(model)
            for field in patch.model_fields_set:
                values[field] = getattr(patch, field)
            data = ReminderInput.model_validate(values)
            timezone = await self._resolve_reminder_timezone(session, owner_user_id, data.timezone)
            destination = await self._active_destination(session, owner_user_id, data.destination_id)
            scheduled_at, recurrence, next_run_at = self._schedule_values(data, timezone, utc_now())
            model.destination_id = destination.id
            model.title = data.title or ""
            model.notes = data.notes
            model.kind = data.kind
            model.schedule_type = data.schedule_type
            model.scheduled_at = scheduled_at
            model.timezone = timezone
            model.recurrence = recurrence
            model.enabled = data.enabled
            model.next_run_at = next_run_at if data.enabled else None
            workout = await self._repository.workout_for_reminder(session, model.id)
            if workout is not None:
                workout.name = model.title
                workout.enabled = model.enabled
            return self._reminder_value(model)

    async def delete_reminder(self, owner_user_id: int, reminder_id: int) -> None:
        async with self._database.transaction() as session:
            model = await self._repository.reminder(session, owner_user_id, reminder_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            await session.delete(model)

    async def occurrences(self, owner_user_id: int, reminder_id: int) -> list[ReminderOccurrenceValue]:
        async with self._database.session() as session:
            if await self._repository.reminder(session, owner_user_id, reminder_id) is None:
                raise LifeNotFoundError
            return [self._occurrence_value(value) for value in await self._repository.occurrences(session, owner_user_id, reminder_id, limit=100)]

    async def transition_occurrence(self, owner_user_id: int, occurrence_id: int, action: str) -> ReminderOccurrenceValue:
        if action not in {"completed", "skipped"}:
            raise LifeValidationError("Unsupported occurrence action.")
        async with self._database.transaction() as session:
            occurrence = await session.scalar(select(LifeReminderOccurrenceModel).join(LifeReminderModel, LifeReminderModel.id == LifeReminderOccurrenceModel.reminder_id).where(LifeReminderOccurrenceModel.id == occurrence_id, LifeReminderModel.owner_user_id == owner_user_id).with_for_update())
            if occurrence is None:
                raise LifeNotFoundError
            if occurrence.status in {"completed", "skipped"}:
                return self._occurrence_value(occurrence)
            if occurrence.status not in {"sent", "pending"}:
                raise LifeValidationError("This occurrence cannot be changed now.")
            occurrence.status = action
            occurrence.completed_at = utc_now() if action == "completed" else None
            occurrence.claim_token = None
            occurrence.claimed_at = None
            occurrence.lease_expires_at = None
            workout = await self._repository.workout_for_reminder(session, occurrence.reminder_id)
            if workout is not None:
                completion = await self._repository.workout_completion(session, occurrence.id)
                status = "done" if action == "completed" else "skipped"
                if completion is None:
                    session.add(LifeWorkoutCompletionModel(workout_schedule_id=workout.id, occurrence_id=occurrence.id, scheduled_for=occurrence.scheduled_for, status=status, completed_at=occurrence.completed_at))
                else:
                    completion.status, completion.completed_at = status, occurrence.completed_at
            return self._occurrence_value(occurrence)

    async def prepare_due_occurrences(self, bot_id: int) -> None:
        now = utc_now()
        async with self._database.transaction() as session:
            for reminder in await self._repository.due_reminders(session, bot_id=bot_id, now=now, limit=50):
                scheduled_for = reminder.next_run_at
                if scheduled_for is None:
                    continue
                if reminder.schedule_type == "one_time":
                    grace_seconds = reminder.one_time_grace_seconds or self._settings.life_reminder_one_time_grace_seconds
                    status = "missed" if now - scheduled_for > timedelta(seconds=grace_seconds) else "pending"
                    await self._repository.insert_occurrence(session, reminder_id=reminder.id, scheduled_for=scheduled_for, status=status, now=now)
                    reminder.enabled = False
                    reminder.next_run_at = None
                    reminder.last_run_at = scheduled_for
                    continue
                stale_after = timedelta(seconds=self._settings.life_reminder_executor_interval_seconds * 2)
                if now - scheduled_for > stale_after:
                    # Suppress overdue recurring history rather than delivering or backfilling it.
                    await self._repository.insert_occurrence(session, reminder_id=reminder.id, scheduled_for=scheduled_for, status="skipped", now=now)
                    while reminder.next_run_at is not None and reminder.next_run_at <= now:
                        reminder.last_run_at = reminder.next_run_at
                        reminder.next_run_at = self._next_recurring_run(reminder, reminder.next_run_at)
                    continue
                await self._repository.insert_occurrence(session, reminder_id=reminder.id, scheduled_for=scheduled_for, status="pending", now=now)
                reminder.last_run_at = scheduled_for
                reminder.next_run_at = self._next_recurring_run(reminder, scheduled_for)

    async def claim_due_occurrences(self, bot_id: int) -> list[ReminderDeliveryClaim]:
        now = utc_now()
        lease_expires_at = now + timedelta(seconds=self._settings.life_reminder_claim_lease_seconds)
        claims: list[ReminderDeliveryClaim] = []
        async with self._database.transaction() as session:
            for occurrence, reminder, destination, chat in await self._repository.claim_occurrences(session, bot_id=bot_id, now=now, lease_expires_at=lease_expires_at, limit=self._settings.life_reminder_executor_batch_size):
                token = uuid.uuid4().hex
                occurrence.status = "claimed"
                occurrence.claim_token = token
                occurrence.claimed_at = now
                occurrence.lease_expires_at = lease_expires_at
                occurrence.attempts += 1
                recommendation = None
                if reminder.goal_recommendation_id is not None:
                    recommendation = await session.scalar(select(LifeGoalRecommendationModel).where(LifeGoalRecommendationModel.id == reminder.goal_recommendation_id))
                claims.append(ReminderDeliveryClaim(occurrence_id=occurrence.id, claim_token=token, destination_id=destination.id, telegram_chat_id=chat.telegram_chat_id, chat_type=destination.kind, title=reminder.title, kind=reminder.kind, scheduled_for=occurrence.scheduled_for, notes=reminder.notes, goal_recommendation_id=reminder.goal_recommendation_id, goal_recommendation_current_kcal=recommendation.current_calorie_target_kcal if recommendation is not None else None, goal_recommendation_recommended_kcal=recommendation.recommended_calorie_target_kcal if recommendation is not None else None))
        return claims

    async def complete_delivery(self, claim: ReminderDeliveryClaim, message: SentMessage) -> None:
        async with self._database.transaction() as session:
            occurrence = await session.scalar(select(LifeReminderOccurrenceModel).where(LifeReminderOccurrenceModel.id == claim.occurrence_id).with_for_update())
            if occurrence is None or occurrence.status != "claimed" or occurrence.claim_token != claim.claim_token:
                return
            occurrence.status = "sent"
            occurrence.delivered_at = utc_now()
            occurrence.telegram_message_id = message.message_id
            occurrence.claim_token = None
            occurrence.claimed_at = None
            occurrence.lease_expires_at = None
            if claim.goal_recommendation_id is not None:
                recommendation = await session.scalar(select(LifeGoalRecommendationModel).where(LifeGoalRecommendationModel.id == claim.goal_recommendation_id).with_for_update())
                if recommendation is not None:
                    recommendation.telegram_chat_id = claim.telegram_chat_id
                    recommendation.telegram_message_id = message.message_id
                    recommendation.delivery_status = "sent"

    async def fail_delivery(self, claim: ReminderDeliveryClaim, error: Exception) -> None:
        now = utc_now()
        permanent = isinstance(error, TelegramAPIError) and error.telegram_error_code in {400, 403, 404}
        async with self._database.transaction() as session:
            occurrence = await session.scalar(select(LifeReminderOccurrenceModel).where(LifeReminderOccurrenceModel.id == claim.occurrence_id).with_for_update())
            if occurrence is None or occurrence.status != "claimed" or occurrence.claim_token != claim.claim_token:
                return
            occurrence.claim_token = None
            occurrence.claimed_at = None
            occurrence.lease_expires_at = None
            failure_code = "telegram_permanent" if permanent else "telegram_temporary"
            if permanent or occurrence.attempts >= self._settings.life_reminder_max_attempts:
                occurrence.status = "failed"
                occurrence.failure_code = failure_code if permanent else "retry_exhausted"
                occurrence.failure_detail = None
                if claim.goal_recommendation_id is not None:
                    recommendation = await session.scalar(select(LifeGoalRecommendationModel).where(LifeGoalRecommendationModel.id == claim.goal_recommendation_id).with_for_update())
                    if recommendation is not None:
                        recommendation.delivery_status = "failed"
                if permanent:
                    destination = await session.get(LifeNotificationDestinationModel, claim.destination_id, with_for_update=True)
                    if destination is not None:
                        destination.enabled = False
                        destination.is_default = False
                        destination.disabled_reason = "telegram_delivery_unavailable"
                return
            retry_after = error.retry_after if isinstance(error, TelegramAPIError) else None
            delay = retry_after or self._settings.life_reminder_retry_base_seconds * (2 ** (occurrence.attempts - 1))
            occurrence.status = "pending"
            occurrence.available_at = now + timedelta(seconds=delay)
            occurrence.failure_code = failure_code
            occurrence.failure_detail = None

    async def foods(self, owner_user_id: int) -> list[FoodValue]:
        async with self._database.session() as session:
            return [self._food_value(value) for value in await self._repository.foods(session, owner_user_id)]

    async def create_food(self, owner_user_id: int, data: FoodInput) -> FoodValue:
        async with self._database.transaction() as session:
            model = LifeFoodModel(owner_user_id=owner_user_id, **data.model_dump())
            session.add(model)
            await session.flush()
            return self._food_value(model)

    async def patch_food(self, owner_user_id: int, food_id: int, data: FoodPatch) -> FoodValue:
        async with self._database.transaction() as session:
            model = await self._repository.food(session, owner_user_id, food_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            for field in data.model_fields_set:
                setattr(model, field, getattr(data, field))
            return self._food_value(model)

    async def templates(self, owner_user_id: int) -> list[MealTemplateValue]:
        async with self._database.session() as session:
            return [await self._template_value(session, model) for model in await self._repository.templates(session, owner_user_id)]

    async def create_template(self, owner_user_id: int, data: MealTemplateInput) -> MealTemplateValue:
        async with self._database.transaction() as session:
            foods = await self._template_foods(session, owner_user_id, data.items)
            model = LifeMealTemplateModel(owner_user_id=owner_user_id, name=data.name, meal_slot=data.meal_slot, active=data.active)
            session.add(model)
            await session.flush()
            await self._repository.replace_template_items(session, model.id, foods)
            return await self._template_value(session, model)

    async def patch_template(self, owner_user_id: int, template_id: int, data: MealTemplatePatch) -> MealTemplateValue:
        async with self._database.transaction() as session:
            model = await self._repository.template(session, owner_user_id, template_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            for field in ("name", "meal_slot", "active"):
                if field in data.model_fields_set:
                    setattr(model, field, getattr(data, field))
            if data.items is not None:
                await self._repository.replace_template_items(session, model.id, await self._template_foods(session, owner_user_id, data.items))
            return await self._template_value(session, model)

    async def deactivate_template(self, owner_user_id: int, template_id: int) -> None:
        async with self._database.transaction() as session:
            model = await self._repository.template(session, owner_user_id, template_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            model.active = False

    async def meal_logs(self, owner_user_id: int, start_date: date, end_date: date) -> list[MealLogValue]:
        self._validate_range(start_date, end_date)
        async with self._database.session() as session:
            return [await self._meal_log_value(session, value) for value in await self._repository.meal_logs(session, owner_user_id, start_date, end_date)]

    async def create_meal_log(self, owner_user_id: int, data: MealLogInput) -> MealLogValue:
        async with self._database.transaction() as session:
            timezone = await self._owner_timezone(session, owner_user_id)
            foods = await self._template_foods(session, owner_user_id, data.items)
            consumed_at = data.consumed_at.astimezone(UTC)
            model = LifeMealLogModel(owner_user_id=owner_user_id, meal_slot=data.meal_slot, status=data.status, consumed_at=consumed_at, local_date=consumed_at.astimezone(ZoneInfo(timezone)).date(), note=data.note)
            session.add(model)
            await session.flush()
            for position, (food, quantity) in enumerate(foods):
                session.add(LifeMealLogItemModel(meal_log_id=model.id, food_id=food.id, food_name=food.name, quantity=quantity, calories_kcal=int(food.calories_kcal * quantity), protein_g=food.protein_g * quantity, position=position))
            await session.flush()
            return await self._meal_log_value(session, model)

    async def delete_meal_log(self, owner_user_id: int, log_id: int) -> None:
        async with self._database.transaction() as session:
            model = await self._repository.meal_log(session, owner_user_id, log_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            await session.delete(model)

    async def weights(self, owner_user_id: int, start_date: date, end_date: date) -> list[WeightLogValue]:
        self._validate_range(start_date, end_date)
        async with self._database.session() as session:
            return [self._weight_value(value) for value in await self._repository.weight_logs(session, owner_user_id, start_date, end_date)]

    async def put_weight(self, owner_user_id: int, data: WeightLogInput) -> WeightLogValue:
        async with self._database.transaction() as session:
            timezone = await self._owner_timezone(session, owner_user_id)
            weighed_at = data.weighed_at.astimezone(UTC)
            local_date = weighed_at.astimezone(ZoneInfo(timezone)).date()
            model = await self._repository.weight_log_for_date(session, owner_user_id, local_date, locked=True)
            if model is None:
                model = LifeWeightLogModel(owner_user_id=owner_user_id, weighed_at=weighed_at, local_date=local_date, weight_kg=data.weight_kg, note=data.note)
                session.add(model)
                await session.flush()
            else:
                model.weighed_at, model.weight_kg, model.note = weighed_at, data.weight_kg, data.note
            return self._weight_value(model)

    async def delete_weight(self, owner_user_id: int, log_id: int) -> None:
        async with self._database.transaction() as session:
            values = await session.scalars(select(LifeWeightLogModel).where(LifeWeightLogModel.id == log_id, LifeWeightLogModel.owner_user_id == owner_user_id).with_for_update())
            model = values.one_or_none()
            if model is None:
                raise LifeNotFoundError
            await session.delete(model)

    async def workouts(self, owner_user_id: int) -> list[WorkoutScheduleValue]:
        async with self._database.session() as session:
            return [await self._workout_value(session, value) for value in await self._repository.workout_schedules(session, owner_user_id)]

    async def create_workout(self, owner_user_id: int, data: WorkoutScheduleInput) -> WorkoutScheduleValue:
        async with self._database.transaction() as session:
            reminder = await self._create_reminder_in_session(session, owner_user_id, data.reminder)
            model = LifeWorkoutScheduleModel(owner_user_id=owner_user_id, reminder_id=reminder.id, name=data.name, workout_type=data.workout_type, enabled=reminder.enabled)
            session.add(model)
            await session.flush()
            return await self._workout_value(session, model)

    async def patch_workout(self, owner_user_id: int, schedule_id: int, data: WorkoutSchedulePatch) -> WorkoutScheduleValue:
        async with self._database.transaction() as session:
            model = await self._repository.workout_schedule(session, owner_user_id, schedule_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            if data.name is not None:
                model.name = data.name
            if "workout_type" in data.model_fields_set:
                model.workout_type = data.workout_type
            if data.reminder is not None:
                reminder = await self._patch_reminder_in_session(session, owner_user_id, model.reminder_id, data.reminder)
                model.enabled = reminder.enabled
            elif data.enabled is not None:
                reminder = await self._repository.reminder(session, owner_user_id, model.reminder_id, locked=True)
                assert reminder is not None
                reminder.enabled = data.enabled
                if not data.enabled:
                    reminder.next_run_at = None
                model.enabled = data.enabled
            return await self._workout_value(session, model)

    async def complete_workout(self, owner_user_id: int, schedule_id: int, occurrence_id: int, data: WorkoutCompletionInput) -> WorkoutCompletionValue:
        async with self._database.transaction() as session:
            schedule = await self._repository.workout_schedule(session, owner_user_id, schedule_id, locked=True)
            if schedule is None:
                raise LifeNotFoundError
            occurrence = await session.scalar(select(LifeReminderOccurrenceModel).where(LifeReminderOccurrenceModel.id == occurrence_id, LifeReminderOccurrenceModel.reminder_id == schedule.reminder_id).with_for_update())
            if occurrence is None:
                raise LifeNotFoundError
            if occurrence.status not in {"sent", "pending", "completed", "skipped"}:
                raise LifeValidationError("This workout occurrence cannot be changed now.")
            occurrence.status = "completed" if data.status == "done" else "skipped"
            occurrence.completed_at = utc_now() if data.status == "done" else None
            completion = await self._repository.workout_completion(session, occurrence.id)
            if completion is None:
                completion = LifeWorkoutCompletionModel(workout_schedule_id=schedule.id, occurrence_id=occurrence.id, scheduled_for=occurrence.scheduled_for, status=data.status, completed_at=occurrence.completed_at, note=data.note)
                session.add(completion)
                await session.flush()
            else:
                completion.status, completion.completed_at, completion.note = data.status, occurrence.completed_at, data.note
            return self._completion_value(completion)

    async def today(self, owner_user_id: int) -> TodayValue:
        async with self._database.session() as session:
            timezone = await self._owner_timezone(session, owner_user_id)
            current_date = utc_now().astimezone(ZoneInfo(timezone)).date()
            meals = [await self._meal_log_value(session, value) for value in await self._repository.meal_logs(session, owner_user_id, current_date, current_date)]
            logged = [value for value in meals if value.status == "logged"]
            goal = await self._goal_for_date(session, owner_user_id, current_date)
            workouts = await self._repository.workout_schedules(session, owner_user_id)
            workout = next((value for value in workouts if value.enabled), None)
            workout_value = await self._workout_value(session, workout) if workout else None
            completion = None
            workout_occurrence_id = None
            if workout:
                occurrences = await self._repository.occurrences(session, owner_user_id, workout.reminder_id, limit=5)
                current = next((value for value in occurrences if value.scheduled_for.astimezone(ZoneInfo(timezone)).date() == current_date), None)
                if current:
                    workout_occurrence_id = current.id
                    model = await self._repository.workout_completion(session, current.id)
                    completion = self._completion_value(model) if model else None
            reminders = [self._reminder_value(value) for value in await self._repository.reminders(session, owner_user_id) if value.enabled and value.next_run_at is not None][:10]
            return TodayValue(date=current_date, timezone=timezone, calorie_target_kcal=goal.calorie_target_kcal if goal else None, protein_min_g=goal.protein_min_g if goal else None, protein_max_g=goal.protein_max_g if goal else None, calories_consumed=sum(value.calories_kcal for value in logged), protein_consumed=sum((value.protein_g for value in logged), start=0), meals=meals, workout=workout_value, workout_occurrence_id=workout_occurrence_id, workout_completion=completion, upcoming_reminders=reminders)

    async def progress(self, owner_user_id: int, start_date: date, end_date: date) -> ProgressValue:
        self._validate_range(start_date, end_date, maximum_days=90)
        async with self._database.session() as session:
            timezone = await self._owner_timezone(session, owner_user_id)
            zone = ZoneInfo(timezone)
            meals = await self._repository.meal_logs(session, owner_user_id, start_date, end_date)
            by_date: dict[date, tuple[int, object]] = {}
            for meal in meals:
                if meal.status != "logged":
                    continue
                items = await self._repository.meal_log_items(session, meal.id)
                calories, protein = by_date.get(meal.local_date, (0, 0))
                by_date[meal.local_date] = (calories + sum(item.calories_kcal for item in items), protein + sum((item.protein_g for item in items), start=0))
            completion_counts: dict[date, tuple[int, int]] = {}
            range_start = datetime.combine(start_date, time.min, tzinfo=zone).astimezone(UTC)
            range_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
            for completion in await self._repository.workout_completions(session, owner_user_id, range_start, range_end):
                local_date = completion.scheduled_for.astimezone(zone).date()
                done, skipped = completion_counts.get(local_date, (0, 0))
                completion_counts[local_date] = (done + (completion.status == "done"), skipped + (completion.status == "skipped"))
            days: list[ProgressDayValue] = []
            current = start_date
            while current <= end_date:
                goal = await self._goal_for_date(session, owner_user_id, current)
                calories, protein = by_date.get(current, (0, 0))
                done, skipped = completion_counts.get(current, (0, 0))
                days.append(ProgressDayValue(date=current, calories_consumed=calories, calorie_target_kcal=goal.calorie_target_kcal if goal else None, protein_consumed=protein, protein_min_g=goal.protein_min_g if goal else None, workout_done=done, workout_skipped=skipped))
                current += timedelta(days=1)
            return ProgressValue(start_date=start_date, end_date=end_date, days=days, weights=[self._weight_value(value) for value in await self._repository.weight_logs(session, owner_user_id, start_date, end_date)])

    async def grocery_lists(self, owner_user_id: int) -> list[GroceryListValue]:
        async with self._database.session() as session:
            return [await self._grocery_list_value(session, value) for value in await self._repository.grocery_lists(session, owner_user_id)]

    async def rotate_due_grocery_lists(self, bot_id: int) -> int:
        now = utc_now()
        rotated = 0
        async with self._database.transaction() as session:
            candidates = await self._repository.grocery_lists_for_automation(session, limit=self._settings.life_reminder_executor_batch_size)
            for candidate in candidates:
                await self._repository.lock_owner(session, candidate.owner_user_id)
                model = await self._repository.grocery_list(session, candidate.owner_user_id, candidate.id, locked=True)
                if model is None or model.status != "active":
                    continue
                profile = await self._repository.profile(session, model.owner_user_id)
                if profile is None:
                    continue
                self._validate_timezone(profile.timezone)
                local_date = now.astimezone(ZoneInfo(profile.timezone)).date()
                if local_date < model.ends_on:
                    continue
                items = await self._repository.grocery_items(session, model.id)
                unbought = [item for item in items if not item.is_bought]
                if unbought and model.unbought_reminder_id is None:
                    destination_context = await self._repository.notification_destination_for_bot(session, model.owner_user_id, bot_id)
                    if destination_context is not None:
                        destination, _chat = destination_context
                        item_lines = "\n".join(f"• {item.name} — {item.quantity} {item.unit}" for item in unbought)
                        reminder = LifeReminderModel(
                            owner_user_id=model.owner_user_id,
                            destination_id=destination.id,
                            title=f"Grocery checklist: {model.name}"[:255],
                            notes=("Please check off these unbought items in Life:\n" + item_lines + "\n\nThis reminder expires in 24 hours.")[:1000],
                            kind="grocery",
                            schedule_type="one_time",
                            scheduled_at=now,
                            timezone=profile.timezone,
                            recurrence=None,
                            enabled=True,
                            one_time_grace_seconds=86_400,
                            next_run_at=now,
                        )
                        session.add(reminder)
                        await session.flush()
                        model.unbought_reminder_id = reminder.id
                if local_date == model.ends_on:
                    continue
                model.status = "archived"
                if model.cadence == "custom":
                    rotated += 1
                    continue
                await session.flush()
                starts_on, ends_on = self._next_grocery_period(model.cadence, model.ends_on + timedelta(days=1))
                while ends_on < local_date:
                    starts_on, ends_on = self._next_grocery_period(model.cadence, ends_on + timedelta(days=1))
                session.add(LifeGroceryListModel(owner_user_id=model.owner_user_id, name=model.name, cadence=model.cadence, starts_on=starts_on, ends_on=ends_on, status="active"))
                rotated += 1
        return rotated

    async def create_grocery_list(self, owner_user_id: int, data: GroceryListInput) -> GroceryListValue:
        async with self._database.transaction() as session:
            await self._repository.lock_owner(session, owner_user_id)
            if await self._repository.active_grocery_list(session, owner_user_id, locked=True) is not None:
                raise LifeValidationError("Archive the active grocery list before creating a new one.")
            if data.cadence == "custom":
                starts_on, ends_on = self._grocery_period(data.cadence, starts_on=data.starts_on, ends_on=data.ends_on)
            else:
                profile = await self._repository.profile(session, owner_user_id, locked=True)
                if profile is None:
                    raise LifeValidationError("Create a Life profile with a timezone first.")
                self._validate_timezone(profile.timezone)
                starts_on, ends_on = self._grocery_period(data.cadence, utc_now().astimezone(ZoneInfo(profile.timezone)).date())
            model = LifeGroceryListModel(owner_user_id=owner_user_id, name=data.name, cadence=data.cadence, starts_on=starts_on, ends_on=ends_on, status="active")
            session.add(model)
            await session.flush()
            return await self._grocery_list_value(session, model)

    async def patch_grocery_list(self, owner_user_id: int, list_id: int, data: GroceryListPatch) -> GroceryListValue:
        async with self._database.transaction() as session:
            await self._repository.lock_owner(session, owner_user_id)
            model = await self._repository.grocery_list(session, owner_user_id, list_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            values = {"name": model.name, "cadence": model.cadence, "starts_on": model.starts_on, "ends_on": model.ends_on, "status": model.status}
            for field in data.model_fields_set:
                values[field] = getattr(data, field)
            cadence = values["cadence"]
            if cadence != "custom":
                starts_on, ends_on = await self._resolved_grocery_period(session, owner_user_id, cadence)
                values["starts_on"] = starts_on
                values["ends_on"] = ends_on
            elif model.cadence != "custom" and not {"starts_on", "ends_on"}.issubset(data.model_fields_set):
                raise LifeValidationError("starts_on and ends_on are required when changing cadence to custom.")
            if values["starts_on"] is None or values["ends_on"] is None:
                raise LifeValidationError("starts_on and ends_on are required for custom cadence.")
            try:
                valid = GroceryListState.model_validate(values)
            except ValidationError as error:
                raise LifeValidationError("The grocery list period is invalid.") from error
            if valid.status == "active" and model.status != "active":
                active = await self._repository.active_grocery_list(session, owner_user_id, locked=True)
                if active is not None and active.id != model.id:
                    raise LifeValidationError("Archive the active grocery list before activating another one.")
            for field, value in valid.model_dump().items():
                setattr(model, field, value)
            return await self._grocery_list_value(session, model)

    async def archive_grocery_list(self, owner_user_id: int, list_id: int) -> GroceryListValue:
        async with self._database.transaction() as session:
            await self._repository.lock_owner(session, owner_user_id)
            model = await self._repository.grocery_list(session, owner_user_id, list_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            model.status = "archived"
            return await self._grocery_list_value(session, model)

    async def delete_grocery_list(self, owner_user_id: int, list_id: int) -> None:
        async with self._database.transaction() as session:
            await self._repository.lock_owner(session, owner_user_id)
            model = await self._repository.grocery_list(session, owner_user_id, list_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            await session.delete(model)

    async def add_grocery_item(self, owner_user_id: int, list_id: int, data: GroceryItemInput) -> GroceryItemValue:
        async with self._database.transaction() as session:
            if await self._repository.grocery_list(session, owner_user_id, list_id, locked=True) is None:
                raise LifeNotFoundError
            items = await self._repository.grocery_items(session, list_id)
            model = LifeGroceryItemModel(list_id=list_id, **data.model_dump(), position=len(items))
            session.add(model)
            await session.flush()
            return self._grocery_item_value(model)

    async def patch_grocery_item(self, owner_user_id: int, list_id: int, item_id: int, data: GroceryItemPatch) -> GroceryItemValue:
        async with self._database.transaction() as session:
            model = await self._repository.grocery_item(session, owner_user_id, list_id, item_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            for field in data.model_fields_set:
                value = getattr(data, field)
                if field == "is_bought":
                    model.is_bought = value
                    model.bought_at = utc_now() if value else None
                else:
                    setattr(model, field, value)
            return self._grocery_item_value(model)

    async def delete_grocery_item(self, owner_user_id: int, list_id: int, item_id: int) -> None:
        async with self._database.transaction() as session:
            model = await self._repository.grocery_item(session, owner_user_id, list_id, item_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            await session.delete(model)

    async def recurring_grocery_items(self, owner_user_id: int) -> list[RecurringGroceryItemValue]:
        async with self._database.session() as session:
            return [self._recurring_grocery_value(value) for value in await self._repository.recurring_grocery_items(session, owner_user_id)]

    async def create_recurring_grocery_item(self, owner_user_id: int, data: RecurringGroceryItemInput) -> RecurringGroceryItemValue:
        async with self._database.transaction() as session:
            model = LifeRecurringGroceryItemModel(owner_user_id=owner_user_id, **data.model_dump())
            session.add(model)
            await session.flush()
            return self._recurring_grocery_value(model)

    async def patch_recurring_grocery_item(self, owner_user_id: int, item_id: int, data: RecurringGroceryItemPatch) -> RecurringGroceryItemValue:
        async with self._database.transaction() as session:
            model = await self._repository.recurring_grocery_item(session, owner_user_id, item_id, locked=True)
            if model is None:
                raise LifeNotFoundError
            for field in data.model_fields_set:
                setattr(model, field, getattr(data, field))
            return self._recurring_grocery_value(model)

    async def add_recurring_grocery_item(self, owner_user_id: int, list_id: int, recurring_id: int) -> GroceryItemValue:
        async with self._database.transaction() as session:
            recurring = await self._repository.recurring_grocery_item(session, owner_user_id, recurring_id)
            if recurring is None or not recurring.enabled:
                raise LifeNotFoundError
            if await self._repository.grocery_list(session, owner_user_id, list_id, locked=True) is None:
                raise LifeNotFoundError
            items = await self._repository.grocery_items(session, list_id)
            model = LifeGroceryItemModel(list_id=list_id, name=recurring.name, quantity=recurring.quantity, unit=recurring.unit, estimated_unit_price_rupiah=recurring.estimated_unit_price_rupiah, position=len(items))
            session.add(model)
            await session.flush()
            return self._grocery_item_value(model)

    async def _create_reminder_in_session(self, session: AsyncSession, owner_user_id: int, data: ReminderInput) -> LifeReminderModel:
        timezone = await self._resolve_reminder_timezone(session, owner_user_id, data.timezone)
        destination = await self._active_destination(session, owner_user_id, data.destination_id)
        scheduled_at, recurrence, next_run_at = self._schedule_values(data, timezone, utc_now())
        model = LifeReminderModel(owner_user_id=owner_user_id, destination_id=destination.id, title=data.title or "", notes=data.notes, kind="workout", schedule_type=data.schedule_type, scheduled_at=scheduled_at, timezone=timezone, recurrence=recurrence, enabled=data.enabled, next_run_at=next_run_at if data.enabled else None)
        session.add(model)
        await session.flush()
        return model

    async def _patch_reminder_in_session(self, session: AsyncSession, owner_user_id: int, reminder_id: int, patch: ReminderPatch) -> LifeReminderModel:
        model = await self._repository.reminder(session, owner_user_id, reminder_id, locked=True)
        if model is None:
            raise LifeNotFoundError
        values = self._reminder_input_values(model)
        for field in patch.model_fields_set:
            values[field] = getattr(patch, field)
        data = ReminderInput.model_validate(values)
        timezone = await self._resolve_reminder_timezone(session, owner_user_id, data.timezone)
        destination = await self._active_destination(session, owner_user_id, data.destination_id)
        scheduled_at, recurrence, next_run_at = self._schedule_values(data, timezone, utc_now())
        model.destination_id, model.title, model.notes, model.kind = destination.id, data.title or "", data.notes, "workout"
        model.schedule_type, model.scheduled_at, model.timezone, model.recurrence = data.schedule_type, scheduled_at, timezone, recurrence
        model.enabled, model.next_run_at = data.enabled, next_run_at if data.enabled else None
        return model

    async def _template_foods(self, session: AsyncSession, owner_user_id: int, items) -> list[tuple[LifeFoodModel, object]]:
        values: list[tuple[LifeFoodModel, object]] = []
        seen: set[int] = set()
        for item in items:
            if item.food_id in seen:
                raise LifeValidationError("A food may appear once in a meal item list.")
            seen.add(item.food_id)
            food = await self._repository.food(session, owner_user_id, item.food_id)
            if food is None or not food.active:
                raise LifeValidationError("Select an active food you own.")
            values.append((food, item.quantity))
        return values

    async def _owner_timezone(self, session: AsyncSession, owner_user_id: int) -> str:
        profile = await self._repository.profile(session, owner_user_id)
        if profile is None:
            raise LifeValidationError("Create a Life profile with a timezone first.")
        self._validate_timezone(profile.timezone)
        return profile.timezone

    async def _goal_for_date(self, session: AsyncSession, owner_user_id: int, target_date: date) -> LifeNutritionGoalModel | None:
        goals = await self._repository.goals(session, owner_user_id)
        return next((goal for goal in goals if goal.effective_from <= target_date), None)

    @staticmethod
    def _validate_range(start_date: date, end_date: date, maximum_days: int = 31) -> None:
        if end_date < start_date or (end_date - start_date).days > maximum_days:
            raise LifeValidationError(f"Date range must be between zero and {maximum_days} days.")

    @staticmethod
    def _food_value(model: LifeFoodModel) -> FoodValue:
        return FoodValue(id=model.id, name=model.name, serving_label=model.serving_label, serving_grams=model.serving_grams, calories_kcal=model.calories_kcal, protein_g=model.protein_g, active=model.active, created_at=model.created_at, updated_at=model.updated_at)

    async def _template_value(self, session: AsyncSession, model: LifeMealTemplateModel) -> MealTemplateValue:
        items = [MealTemplateItemValue(id=item.id, food_id=food.id, food_name=food.name, quantity=item.quantity, position=item.position) for item, food in await self._repository.template_items(session, model.id)]
        return MealTemplateValue(id=model.id, name=model.name, meal_slot=model.meal_slot, active=model.active, items=items, created_at=model.created_at, updated_at=model.updated_at)

    async def _meal_log_value(self, session: AsyncSession, model: LifeMealLogModel) -> MealLogValue:
        items = [MealLogItemValue(id=item.id, food_id=item.food_id, food_name=item.food_name, quantity=item.quantity, calories_kcal=item.calories_kcal, protein_g=item.protein_g, position=item.position) for item in await self._repository.meal_log_items(session, model.id)]
        return MealLogValue(id=model.id, meal_slot=model.meal_slot, status=model.status, consumed_at=model.consumed_at, local_date=model.local_date, note=model.note, items=items, calories_kcal=sum(item.calories_kcal for item in items), protein_g=sum((item.protein_g for item in items), start=0), created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _weight_value(model: LifeWeightLogModel) -> WeightLogValue:
        return WeightLogValue(id=model.id, weighed_at=model.weighed_at, local_date=model.local_date, weight_kg=model.weight_kg, note=model.note, created_at=model.created_at, updated_at=model.updated_at)

    async def _workout_value(self, session: AsyncSession, model: LifeWorkoutScheduleModel) -> WorkoutScheduleValue:
        reminder = await self._repository.reminder(session, model.owner_user_id, model.reminder_id)
        assert reminder is not None
        return WorkoutScheduleValue(id=model.id, name=model.name, workout_type=model.workout_type, enabled=model.enabled, reminder=self._reminder_value(reminder), created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _completion_value(model: LifeWorkoutCompletionModel) -> WorkoutCompletionValue:
        return WorkoutCompletionValue(id=model.id, workout_schedule_id=model.workout_schedule_id, occurrence_id=model.occurrence_id, scheduled_for=model.scheduled_for, status=model.status, completed_at=model.completed_at, note=model.note)

    @staticmethod
    def _grocery_item_value(model: LifeGroceryItemModel) -> GroceryItemValue:
        total = None if model.estimated_unit_price_rupiah is None else int(model.quantity * model.estimated_unit_price_rupiah)
        return GroceryItemValue(id=model.id, name=model.name, quantity=model.quantity, unit=model.unit, estimated_unit_price_rupiah=model.estimated_unit_price_rupiah, estimated_total_rupiah=total, is_bought=model.is_bought, bought_at=model.bought_at, position=model.position)

    async def _grocery_list_value(self, session: AsyncSession, model: LifeGroceryListModel) -> GroceryListValue:
        items = [self._grocery_item_value(value) for value in await self._repository.grocery_items(session, model.id)]
        return GroceryListValue(id=model.id, name=model.name, cadence=model.cadence, starts_on=model.starts_on, ends_on=model.ends_on, status=model.status, items=items, estimated_total_rupiah=sum(item.estimated_total_rupiah or 0 for item in items), created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _recurring_grocery_value(model: LifeRecurringGroceryItemModel) -> RecurringGroceryItemValue:
        return RecurringGroceryItemValue(id=model.id, name=model.name, quantity=model.quantity, unit=model.unit, estimated_unit_price_rupiah=model.estimated_unit_price_rupiah, enabled=model.enabled)

    async def _resolve_reminder_timezone(self, session: AsyncSession, owner_user_id: int, requested: str | None) -> str:
        timezone = requested
        if timezone is None:
            profile = await self._repository.profile(session, owner_user_id)
            if profile is None:
                raise LifeValidationError("Create a Life profile with a timezone first.")
            timezone = profile.timezone
        self._validate_timezone(timezone)
        return timezone

    async def _resolved_grocery_period(self, session: AsyncSession, owner_user_id: int, cadence: str) -> tuple[date, date]:
        timezone = await self._owner_timezone(session, owner_user_id)
        current_date = utc_now().astimezone(ZoneInfo(timezone)).date()
        return self._grocery_period(cadence, current_date)

    @staticmethod
    def _grocery_period(cadence: str, current_date: date | None = None, *, starts_on: date | None = None, ends_on: date | None = None) -> tuple[date, date]:
        if cadence == "custom":
            if starts_on is None or ends_on is None:
                raise LifeValidationError("starts_on and ends_on are required for custom cadence.")
            if ends_on < starts_on:
                raise LifeValidationError("ends_on must not precede starts_on.")
            return starts_on, ends_on
        if current_date is None:
            raise LifeValidationError("A current date is required for scheduled cadence.")
        if cadence == "weekly":
            starts_on = current_date - timedelta(days=current_date.weekday())
            return starts_on, starts_on + timedelta(days=6)
        if cadence == "monthly":
            next_month = current_date.month % 12 + 1
            next_year = current_date.year + (current_date.month == 12)
            first_of_following_month = date(next_year, next_month, 1)
            first_of_month_after_following = date(
                next_year + (next_month == 12),
                next_month % 12 + 1,
                1,
            )
            last_day_of_following_month = (first_of_month_after_following - timedelta(days=1)).day
            same_day_next_month = first_of_following_month.replace(day=min(current_date.day, last_day_of_following_month))
            return current_date, same_day_next_month - timedelta(days=1)
        raise LifeValidationError("Unsupported grocery list cadence.")

    @staticmethod
    def _next_grocery_period(cadence: str, starts_on: date) -> tuple[date, date]:
        if cadence == "weekly":
            starts_on += timedelta(days=(7 - starts_on.weekday()) % 7)
            return starts_on, starts_on + timedelta(days=6)
        return LifeService._grocery_period(cadence, starts_on)

    async def _active_destination(self, session: AsyncSession, owner_user_id: int, destination_id: int) -> LifeNotificationDestinationModel:
        destination = await self._repository.destination(session, owner_user_id, destination_id)
        if destination is None:
            raise LifeNotFoundError
        if not destination.enabled or destination.verified_at is None:
            raise LifeValidationError("Select an enabled verified notification destination.")
        return destination

    def _schedule_values(self, data: ReminderInput, timezone: str, now: datetime) -> tuple[datetime | None, dict[str, object] | None, datetime]:
        if data.schedule_type == "one_time":
            assert data.scheduled_at is not None
            scheduled_at = data.scheduled_at.astimezone(UTC)
            return scheduled_at, None, scheduled_at
        assert data.recurrence is not None
        recurrence = data.recurrence.model_dump(mode="json")
        return None, recurrence, self._next_local_occurrence(timezone, data.recurrence, now)

    def _next_recurring_run(self, reminder: LifeReminderModel, after: datetime) -> datetime:
        rule = RecurrenceRule.model_validate(reminder.recurrence)
        return self._next_local_occurrence(reminder.timezone, rule, after + timedelta(seconds=1))

    def _next_local_occurrence(self, timezone: str, rule: RecurrenceRule, after: datetime) -> datetime:
        zone = ZoneInfo(timezone)
        local_after = after.astimezone(zone)
        for offset in range(0, 15):
            candidate_date = local_after.date() + timedelta(days=offset)
            if rule.frequency == "weekly" and candidate_date.weekday() not in {_WEEKDAY_NUMBERS[value] for value in rule.weekdays}:
                continue
            candidate = self._safe_local_datetime(candidate_date, rule.time, zone)
            if candidate > local_after:
                return candidate.astimezone(UTC)
        raise LifeValidationError("Unable to compute the next recurring occurrence.")

    @staticmethod
    def _safe_local_datetime(day, clock: time, zone: ZoneInfo) -> datetime:
        candidate = datetime.combine(day, clock, tzinfo=zone, fold=0)
        # Ambiguous local times use fold=0 (earlier offset). Walk gaps forward to first valid local minute.
        while candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != candidate.replace(tzinfo=None):
            candidate += timedelta(minutes=1)
        return candidate

    @staticmethod
    def _reminder_input_values(model: LifeReminderModel) -> dict[str, object]:
        return {"title": model.title, "notes": model.notes, "kind": model.kind, "schedule_type": model.schedule_type, "scheduled_at": model.scheduled_at, "timezone": model.timezone, "recurrence": model.recurrence, "destination_id": model.destination_id, "enabled": model.enabled}

    @staticmethod
    def _reminder_value(model: LifeReminderModel) -> ReminderValue:
        return ReminderValue(id=model.id, title=model.title, notes=model.notes, kind=model.kind, schedule_type=model.schedule_type, scheduled_at=model.scheduled_at, timezone=model.timezone, recurrence=RecurrenceRule.model_validate(model.recurrence) if model.recurrence else None, destination_id=model.destination_id, enabled=model.enabled, next_run_at=model.next_run_at, last_run_at=model.last_run_at, created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _occurrence_value(model: LifeReminderOccurrenceModel) -> ReminderOccurrenceValue:
        return ReminderOccurrenceValue(id=model.id, reminder_id=model.reminder_id, scheduled_for=model.scheduled_for, status=model.status, attempts=model.attempts, delivered_at=model.delivered_at, completed_at=model.completed_at, failure_code=model.failure_code)

    async def _has_default(self, session: AsyncSession, owner_user_id: int) -> bool:
        return any(model.is_default and model.enabled for model, _, _ in await self._repository.destinations(session, owner_user_id))

    @staticmethod
    def _validate_timezone(value: str) -> None:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise LifeValidationError("Timezone must be a valid IANA timezone.") from error

    @staticmethod
    def _profile_value(model: LifeProfileModel) -> LifeProfileValue:
        return LifeProfileValue(id=model.id, timezone=model.timezone, display_name=model.display_name, height_cm=model.height_cm, sex=model.sex, created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _goal_value(model: LifeNutritionGoalModel) -> NutritionGoalValue:
        return NutritionGoalValue(id=model.id, calorie_target_kcal=model.calorie_target_kcal, protein_min_g=model.protein_min_g, protein_max_g=model.protein_max_g, effective_from=model.effective_from, created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _goal_preference_value(model: LifeGoalPreferenceModel) -> GoalPreferenceValue:
        return GoalPreferenceValue(id=model.id, goal_direction=model.goal_direction, desired_weekly_change_kg=model.desired_weekly_change_kg, last_evaluated_on=model.last_evaluated_on, created_at=model.created_at, updated_at=model.updated_at)

    @staticmethod
    def _goal_recommendation_value(model: LifeGoalRecommendationModel) -> GoalRecommendationValue:
        return GoalRecommendationValue(id=model.id, status=model.status, delivery_status=model.delivery_status, current_goal_id=model.current_goal_id, current_calorie_target_kcal=model.current_calorie_target_kcal, recommended_calorie_target_kcal=model.recommended_calorie_target_kcal, goal_direction=model.goal_direction, desired_weekly_change_kg=model.desired_weekly_change_kg, window_start=model.window_start, window_end=model.window_end, observation_count=model.observation_count, trend_kg_per_week=model.trend_kg_per_week, rule_version=model.rule_version, rule_snapshot=model.rule_snapshot, offered_at=model.offered_at, expires_at=model.expires_at, decided_at=model.decided_at)

    @staticmethod
    def _chat_label(chat: object) -> str:
        title = getattr(chat, "title")
        if title:
            return title
        names = " ".join(item for item in (getattr(chat, "first_name", None), getattr(chat, "last_name", None)) if item)
        return names or getattr(chat, "username", None) or "Telegram chat"

    def _candidate_value(self, candidate, bot, chat) -> DestinationCandidateValue:
        return DestinationCandidateValue(id=candidate.id, bot_name=bot.name, kind=chat.type, chat_label=self._chat_label(chat), last_seen_at=candidate.last_seen_at)

    def _destination_value(self, destination, bot, chat) -> NotificationDestinationValue:
        return NotificationDestinationValue(id=destination.id, bot_name=bot.name, kind=destination.kind, label=destination.label or self._chat_label(chat), enabled=destination.enabled, is_default=destination.is_default, verified_at=destination.verified_at, disabled_reason=destination.disabled_reason, created_at=destination.created_at, updated_at=destination.updated_at)


class LifeReminderExecutor:
    """Database-backed reminder executor independent from FastAPI request handling."""

    def __init__(self, *, bot_id: int, service: LifeService, deliver: Callable[[ReminderDeliveryClaim], Awaitable[SentMessage]]) -> None:
        self._bot_id = bot_id
        self._service = service
        self._deliver = deliver
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name=f"life-reminder-executor-{self._bot_id}")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        await logger.ainfo("life_reminder_executor_started", bot_id=self._bot_id)
        while not self._stop.is_set():
            try:
                await self._service.rotate_due_grocery_lists(self._bot_id)
                await self._service.evaluate_goal_recommendations(self._bot_id)
                await self._service.prepare_due_occurrences(self._bot_id)
                claims = await self._service.claim_due_occurrences(self._bot_id)
                for claim in claims:
                    try:
                        message = await self._deliver(claim)
                        await self._service.complete_delivery(claim, message)
                        await logger.ainfo("life_reminder_delivery_completed", occurrence_id=claim.occurrence_id, destination_id=claim.destination_id)
                    except Exception as error:
                        await self._service.fail_delivery(claim, error)
                        await logger.awarning("life_reminder_delivery_failed", occurrence_id=claim.occurrence_id, destination_id=claim.destination_id, error_type=type(error).__name__)
            except Exception as error:
                await logger.aexception("life_reminder_executor_tick_failed", bot_id=self._bot_id, error_type=type(error).__name__)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._service._settings.life_reminder_executor_interval_seconds)
            except TimeoutError:
                pass
        await logger.ainfo("life_reminder_executor_stopped", bot_id=self._bot_id)
