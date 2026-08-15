from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.core.config import Settings
from app.core.logging import get_logger
from app.core.telegram_client import SentMessage
from app.modules.life.models import LifeNotificationDestinationModel, LifeNutritionGoalModel, LifeProfileModel, LifeReminderModel, LifeReminderOccurrenceModel
from app.modules.life.repositories import LifeRepository
from app.modules.life.schemas import DestinationActivationInput, DestinationCandidateValue, DestinationPatch, LifeProfileInput, LifeProfileValue, NotificationDestinationValue, NutritionGoalInput, NutritionGoalValue, RecurrenceRule, ReminderInput, ReminderOccurrenceValue, ReminderPatch, ReminderValue
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

    async def record_destination_candidate(self, context: UserContext) -> None:
        if context.chat_type not in {"private", "group", "supergroup"}:
            return
        async with self._database.transaction() as session:
            await self._repository.record_candidate(session, owner_user_id=context.internal_user_id, bot_id=context.bot_id, telegram_chat_id=context.chat_id, now=utc_now())

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
        async with self._database.transaction() as session:
            timezone = await self._resolve_reminder_timezone(session, owner_user_id, data.timezone)
            destination = await self._active_destination(session, owner_user_id, data.destination_id)
            scheduled_at, recurrence, next_run_at = self._schedule_values(data, timezone, utc_now())
            model = LifeReminderModel(owner_user_id=owner_user_id, destination_id=destination.id, title=data.title or "", notes=data.notes, kind=data.kind, schedule_type=data.schedule_type, scheduled_at=scheduled_at, timezone=timezone, recurrence=recurrence, enabled=data.enabled, next_run_at=next_run_at if data.enabled else None)
            session.add(model)
            await session.flush()
            return self._reminder_value(model)

    async def patch_reminder(self, owner_user_id: int, reminder_id: int, patch: ReminderPatch) -> ReminderValue:
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
            return self._occurrence_value(occurrence)

    async def prepare_due_occurrences(self, bot_id: int) -> None:
        now = utc_now()
        async with self._database.transaction() as session:
            for reminder in await self._repository.due_reminders(session, bot_id=bot_id, now=now, limit=50):
                scheduled_for = reminder.next_run_at
                if scheduled_for is None:
                    continue
                if reminder.schedule_type == "one_time":
                    status = "missed" if now - scheduled_for > timedelta(seconds=self._settings.life_reminder_one_time_grace_seconds) else "pending"
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
                claims.append(ReminderDeliveryClaim(occurrence_id=occurrence.id, claim_token=token, destination_id=destination.id, telegram_chat_id=chat.telegram_chat_id, chat_type=destination.kind, title=reminder.title, kind=reminder.kind, scheduled_for=occurrence.scheduled_for))
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

    async def _resolve_reminder_timezone(self, session: AsyncSession, owner_user_id: int, requested: str | None) -> str:
        timezone = requested
        if timezone is None:
            profile = await self._repository.profile(session, owner_user_id)
            if profile is None:
                raise LifeValidationError("Create a Life profile with a timezone first.")
            timezone = profile.timezone
        self._validate_timezone(timezone)
        return timezone

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
