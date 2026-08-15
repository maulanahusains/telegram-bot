from __future__ import annotations

import asyncio
import calendar
from collections.abc import Awaitable, Callable, Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.database import Database
from app.core.logging import get_logger
from app.modules.islamic.api import IslamicAPIClient
from app.modules.islamic.models import QuranSessionModel
from app.modules.islamic.repositories import IslamicRepository
from app.modules.islamic.schemas import (
    AyahValue,
    IslamicInputError,
    PrayerClaim,
    ProgressValue,
    ReadUpdate,
    ScopeValue,
    SessionValue,
    StatsValue,
)
from app.shared.utils import utc_now

logger = get_logger(__name__)
TOTAL_QURAN_AYAHS = 6236
TOTAL_QURAN_PAGES = 604
SESSION_TIMEOUT = timedelta(hours=1)
SETUP_MESSAGE_IDS_KEY = "_setup_message_ids"


class IslamicService:
    def __init__(
        self,
        database: Database,
        repository: IslamicRepository,
        api: IslamicAPIClient,
        bot_id: int,
    ) -> None:
        self._database = database
        self._repository = repository
        self._api = api
        self._bot_id = bot_id

    async def ensure_scope(
        self, *, chat_id: int, chat_type: str
    ) -> ScopeValue:
        async with self._database.transaction() as session:
            model = await self._repository.get_or_create_scope(
                session,
                bot_id=self._bot_id,
                chat_id=chat_id,
                chat_type=chat_type,
            )
            return self._scope_value(model)

    async def scope(self, *, chat_id: int) -> ScopeValue | None:
        async with self._database.session() as session:
            model = await self._repository.scope_by_chat(
                session, bot_id=self._bot_id, chat_id=chat_id
            )
            return self._scope_value(model) if model is not None else None

    async def set_setup_state(
        self,
        scope_id: int,
        state: str | None,
        data: dict[str, Any] | None = None,
    ) -> ScopeValue:
        async with self._database.transaction() as session:
            model = await self._repository.scope(session, scope_id, for_update=True)
            if model is None:
                raise IslamicInputError("Scope chat tidak ditemukan.")
            existing_message_ids = self._setup_message_ids(model.setup_data)
            model.setup_state = state
            next_data = dict(data or {})
            if state is not None and state.startswith("setup_") and existing_message_ids:
                next_data[SETUP_MESSAGE_IDS_KEY] = existing_message_ids
            model.setup_data = next_data
            return self._scope_value(model)

    async def replace_setup_message(self, scope_id: int, message_id: int) -> list[int]:
        async with self._database.transaction() as session:
            model = await self._repository.scope(session, scope_id, for_update=True)
            if model is None:
                raise IslamicInputError("Scope chat tidak ditemukan.")
            previous = self._setup_message_ids(model.setup_data)
            data = dict(model.setup_data)
            data[SETUP_MESSAGE_IDS_KEY] = [message_id]
            model.setup_data = data
            return [current for current in previous if current != message_id]

    async def cancel_setup(self, scope_id: int) -> list[int]:
        async with self._database.transaction() as session:
            model = await self._repository.scope(session, scope_id, for_update=True)
            if model is None:
                raise IslamicInputError("Scope chat tidak ditemukan.")
            cleanup = self._setup_message_ids(model.setup_data)
            model.setup_state = None
            model.setup_data = {}
            return cleanup

    async def merge_setup_data(
        self, scope_id: int, *, state: str, values: dict[str, Any]
    ) -> ScopeValue:
        async with self._database.transaction() as session:
            model = await self._repository.scope(session, scope_id, for_update=True)
            if model is None:
                raise IslamicInputError("Scope chat tidak ditemukan.")
            data = dict(model.setup_data)
            data.update(values)
            model.setup_data = data
            model.setup_state = state
            return self._scope_value(model)

    async def detect_timezone(self, data: dict[str, Any]) -> str:
        return await self._api.detect_timezone(
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            city=data.get("city"),
            country=data.get("country"),
        )

    async def methods(self) -> list[tuple[int, str]]:
        return await self._api.calculation_methods()

    async def apply_setup(self, scope_id: int) -> tuple[ScopeValue, list[int]]:
        cleanup: list[int] = []
        async with self._database.transaction() as session:
            model = await self._repository.scope(session, scope_id, for_update=True)
            if model is None:
                raise IslamicInputError("Scope chat tidak ditemukan.")
            data = dict(model.setup_data)
            cleanup.extend(self._setup_message_ids(data))
            timezone_name = self._api.validate_timezone(
                str(data.get("timezone", "Asia/Jakarta"))
            )
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            city = data.get("city")
            country = data.get("country")
            if not (city and country) and (latitude is None or longitude is None):
                raise IslamicInputError("Lokasi setup belum lengkap.")
            model.latitude = float(latitude) if latitude is not None else None
            model.longitude = float(longitude) if longitude is not None else None
            model.city = str(city) if city else None
            model.country = str(country) if country else None
            model.timezone = timezone_name
            raw_method = data.get("method")
            model.calculation_method = int(raw_method) if raw_method is not None else None
            model.configured = True
            model.reminders_enabled = True
            model.setup_state = None
            model.setup_data = {}
            model.last_calendar_check_date = None
            if model.active_reminder_message_id is not None:
                cleanup.append(model.active_reminder_message_id)
                model.active_reminder_message_id = None
            quran_session = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            if quran_session is not None:
                cleanup.extend(self._session_message_ids(quran_session))
                self._expire_session(quran_session, status="cancelled")
            today = utc_now().astimezone(ZoneInfo(timezone_name)).date()
            await self._repository.delete_future_prayers(session, scope_id, today)
            value = self._scope_value(model)
        try:
            await self.sync_scope_month(scope_id)
        except Exception as error:
            await logger.aexception(
                "islamic_initial_calendar_sync_failed",
                scope_id=scope_id,
                error_type=type(error).__name__,
            )
        return value, cleanup

    @staticmethod
    def _setup_message_ids(data: dict[str, Any]) -> list[int]:
        raw = data.get(SETUP_MESSAGE_IDS_KEY, [])
        if not isinstance(raw, list):
            return []
        return [message_id for message_id in raw if isinstance(message_id, int)]

    async def sync_scope_month(
        self, scope_id: int, *, year: int | None = None, month: int | None = None
    ) -> None:
        async with self._database.session() as session:
            model = await self._repository.scope(session, scope_id)
            if model is None or not model.configured:
                return
            local_now = utc_now().astimezone(ZoneInfo(model.timezone))
            year = year or local_now.year
            month = month or local_now.month
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            count = await self._repository.prayer_count(session, scope_id, start, end)
            expected = calendar.monthrange(year, month)[1] * 5
            if count == expected:
                return
            values = self._scope_value(model)
        prayers = await self._api.monthly_prayers(
            year=year,
            month=month,
            latitude=values.latitude,
            longitude=values.longitude,
            city=values.city,
            country=values.country,
            timezone_name=values.timezone,
            method=values.calculation_method,
        )
        async with self._database.transaction() as session:
            await self._repository.upsert_prayers(session, scope_id, prayers)

    async def sync_due_calendars(self) -> None:
        async with self._database.session() as session:
            scopes = list(await self._repository.configured_scopes(session, self._bot_id))
        for model in scopes:
            local_today = utc_now().astimezone(ZoneInfo(model.timezone)).date()
            if model.last_calendar_check_date == local_today:
                continue
            try:
                await self.sync_scope_month(model.id)
                if local_today.day == calendar.monthrange(
                    local_today.year, local_today.month
                )[1]:
                    next_month = (local_today.replace(day=28) + timedelta(days=4)).replace(day=1)
                    await self.sync_scope_month(
                        model.id, year=next_month.year, month=next_month.month
                    )
                async with self._database.transaction() as session:
                    current = await self._repository.scope(session, model.id, for_update=True)
                    if current is not None:
                        current.last_calendar_check_date = local_today
            except Exception as error:
                await logger.aexception(
                    "islamic_calendar_sync_failed",
                    scope_id=model.id,
                    error_type=type(error).__name__,
                )

    async def claim_due_prayers(self) -> list[PrayerClaim]:
        now = utc_now()
        claims: list[PrayerClaim] = []
        async with self._database.transaction() as session:
            schedules = await self._repository.due_prayers(session, now=now)
            for schedule in schedules:
                kind: str | None = None
                if schedule.pre_status == "pending":
                    if now >= schedule.adhan_at:
                        schedule.pre_status = "skipped"
                    elif now >= schedule.adhan_at - timedelta(minutes=15):
                        kind = "pre"
                if kind is None and schedule.adhan_status == "pending":
                    if now > schedule.adhan_at + timedelta(minutes=5):
                        schedule.adhan_status = "skipped"
                    elif now >= schedule.adhan_at:
                        kind = "adhan"
                if kind is None and schedule.quran_status == "pending":
                    if now > schedule.quran_at + timedelta(minutes=60):
                        schedule.quran_status = "skipped"
                    elif now >= schedule.quran_at:
                        kind = "quran"
                if kind is None:
                    continue
                scope = await self._repository.scope(session, schedule.scope_id)
                if scope is None:
                    continue
                skip_message = False
                if kind == "quran":
                    quran_session = await self._repository.session_model(
                        session, scope.id
                    )
                    skip_message = bool(
                        quran_session is not None
                        and quran_session.status in ("awaiting_mode", "active")
                        and quran_session.expires_at is not None
                        and quran_session.expires_at > now
                    )
                schedule.claimed_kind = kind
                schedule.claimed_at = now
                claims.append(
                    PrayerClaim(
                        schedule_id=schedule.id,
                        scope_id=scope.id,
                        chat_id=scope.chat_id,
                        prayer_name=schedule.prayer_name,
                        kind=kind,
                        old_message_id=scope.active_reminder_message_id,
                        skip_message=skip_message,
                    )
                )
        return claims

    async def complete_prayer_claim(
        self, claim: PrayerClaim, new_message_id: int | None
    ) -> None:
        from app.modules.islamic.models import PrayerScheduleModel
        from sqlalchemy import select

        async with self._database.transaction() as session:
            schedule = await session.scalar(
                select(PrayerScheduleModel)
                .where(PrayerScheduleModel.id == claim.schedule_id)
                .with_for_update()
            )
            if schedule is None or schedule.claimed_kind != claim.kind:
                return
            setattr(schedule, f"{claim.kind}_status", "skipped" if claim.skip_message else "sent")
            schedule.claimed_kind = None
            schedule.claimed_at = None
            scope = await self._repository.scope(session, claim.scope_id, for_update=True)
            if scope is not None:
                scope.active_reminder_message_id = new_message_id

    async def release_prayer_claim(self, claim: PrayerClaim) -> None:
        from app.modules.islamic.models import PrayerScheduleModel
        from sqlalchemy import select

        async with self._database.transaction() as session:
            schedule = await session.scalar(
                select(PrayerScheduleModel)
                .where(PrayerScheduleModel.id == claim.schedule_id)
                .with_for_update()
            )
            if schedule is not None and schedule.claimed_kind == claim.kind:
                schedule.claimed_kind = None
                schedule.claimed_at = None

    async def progress(self, scope_id: int) -> ProgressValue:
        async with self._database.transaction() as session:
            model = await self._repository.progress(session, scope_id)
            return self._progress_value(model)

    async def set_progress(self, scope_id: int, ayah: AyahValue | None) -> list[int]:
        cleanup: list[int] = []
        async with self._database.transaction() as session:
            progress = await self._repository.progress(session, scope_id, for_update=True)
            if ayah is None:
                progress.last_ayah_number = 0
                progress.last_surah_number = None
                progress.last_surah_name = None
                progress.last_ayah_in_surah = None
                progress.last_page = None
            else:
                self._apply_ayah(progress, ayah.as_batch_item())
            progress.last_activity_at = None
            quran_session = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            if quran_session is not None:
                cleanup = self._session_message_ids(quran_session)
                self._expire_session(quran_session, status="cancelled")
        return cleanup

    async def resolve_page_position(self, page: int) -> AyahValue:
        if page < 1 or page > TOTAL_QURAN_PAGES:
            raise IslamicInputError("Halaman harus antara 1 dan 604.")
        return (await self._api.page(page))[-1]

    async def resolve_ayah_position(self, reference: str) -> AyahValue:
        return await self._api.ayah_by_reference(reference)

    async def download_image(self, ayah: AyahValue) -> bytes:
        return await self._api.download_image(ayah)

    async def create_read_session(
        self, scope_id: int, amount: int, unit: str
    ) -> tuple[SessionValue, bool, list[int]]:
        if amount < 1 or (unit == "p" and amount > 5) or (unit == "a" and amount > 50):
            raise IslamicInputError("Batas satu sesi adalah 5p atau 50a.")
        async with self._database.transaction() as session:
            scope = await self._repository.scope(session, scope_id)
            if scope is None or not scope.configured:
                raise IslamicInputError("Jalankan /setup terlebih dahulu.")
            progress = await self._repository.progress(session, scope_id)
            start = progress.last_ayah_number + 1
            current = await self._repository.session_model(session, scope_id)
            now = utc_now()
            if (
                current is not None
                and current.status in ("awaiting_mode", "active")
                and current.expires_at is not None
                and current.expires_at > now
            ):
                return self._session_value(current), True, []
        if start > TOTAL_QURAN_AYAHS:
            raise IslamicInputError("Progress sudah mencapai akhir Quran.")
        if unit == "a":
            target = min(TOTAL_QURAN_AYAHS, start + amount - 1)
        else:
            first = await self._api.ayah_by_number(start)
            final_page = min(TOTAL_QURAN_PAGES, first.page + amount - 1)
            target = (await self._api.page(final_page))[-1].number
        now = utc_now()
        cleanup: list[int] = []
        async with self._database.transaction() as session:
            existing = await self._repository.get_or_create_session(session, scope_id)
            if (
                existing is not None
                and existing.status in ("awaiting_mode", "active")
                and existing.expires_at is not None
                and existing.expires_at > now
            ):
                return self._session_value(existing), True, cleanup
            cleanup = self._session_message_ids(existing)
            existing.status = "awaiting_mode"
            existing.mode = None
            existing.target_ayah_number = target
            existing.current_batch = []
            existing.prompt_message_id = None
            existing.last_activity_at = now
            existing.expires_at = now + SESSION_TIMEOUT
            return self._session_value(existing), False, cleanup

    async def attach_prompt(self, session_id: int, message_id: int) -> None:
        from sqlalchemy import select

        async with self._database.transaction() as session:
            model = await session.scalar(
                select(QuranSessionModel)
                .where(QuranSessionModel.id == session_id)
                .with_for_update()
            )
            if model is not None and model.status in ("awaiting_mode", "active"):
                model.prompt_message_id = message_id

    async def active_session(self, scope_id: int, session_id: int) -> SessionValue:
        async with self._database.session() as session:
            model = await self._repository.session_model(session, scope_id)
            self._require_session(model, session_id)
            return self._session_value(model)

    async def choose_mode(self, scope_id: int, session_id: int, mode: str) -> SessionValue:
        if mode not in ("pc", "mobile"):
            raise IslamicInputError("Mode baca tidak valid.")
        async with self._database.transaction() as session:
            model = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            self._require_session(model, session_id)
            model.status = "active"
            model.mode = mode
            model.last_activity_at = utc_now()
            model.expires_at = model.last_activity_at + SESSION_TIMEOUT
            return self._session_value(model)

    async def batch_ayahs(self, scope_id: int, session_id: int) -> list[AyahValue]:
        async with self._database.transaction() as session:
            model = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            self._require_session(model, session_id, active=True)
            if model.current_batch:
                return []
            progress = await self._repository.progress(session, scope_id)
            start = progress.last_ayah_number + 1
            target = int(model.target_ayah_number or 0)
        return await self._api.ayah_range(start, target)

    async def store_batch(
        self, scope_id: int, session_id: int, items: list[dict[str, Any]]
    ) -> None:
        async with self._database.transaction() as session:
            model = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            self._require_session(model, session_id, active=True)
            if model.current_batch:
                raise IslamicInputError("Batch sesi sudah aktif.")
            model.current_batch = items
            model.last_activity_at = utc_now()
            model.expires_at = model.last_activity_at + SESSION_TIMEOUT

    async def mark_read(
        self,
        scope_id: int,
        session_id: int,
        *,
        ayah_number: int | None = None,
        whole_batch: bool = False,
    ) -> ReadUpdate:
        now = utc_now()
        async with self._database.transaction() as session:
            model = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            self._require_session(model, session_id, active=True)
            if not model.current_batch:
                raise IslamicInputError("Batch sesi belum tersedia.")
            items = [dict(item) for item in model.current_batch]
            clicked: dict[str, Any] | None = None
            if whole_batch:
                for item in items:
                    item["read"] = True
                clicked = items[-1]
            else:
                for item in items:
                    if int(item["number"]) == ayah_number:
                        item["read"] = True
                        clicked = item
                        break
                if clicked is None:
                    raise IslamicInputError("Ayat bukan bagian dari batch aktif.")
            progress = await self._repository.progress(session, scope_id, for_update=True)
            previous = progress.last_ayah_number
            last_contiguous: dict[str, Any] | None = None
            expected = previous + 1
            for item in items:
                number = int(item["number"])
                if number < expected:
                    continue
                if number != expected or not item.get("read"):
                    break
                last_contiguous = item
                expected += 1
            if last_contiguous is not None:
                self._apply_ayah(progress, last_contiguous)
                progress.last_activity_at = now
                scope = await self._repository.scope(session, scope_id)
                local_date = now.astimezone(ZoneInfo(scope.timezone)).date()  # type: ignore[union-attr]
                await self._repository.add_daily_stat(
                    session,
                    scope_id=scope_id,
                    local_date=local_date,
                    ayahs=progress.last_ayah_number - previous,
                )
            all_read = all(bool(item.get("read")) for item in items)
            delete_ids: list[int] = []
            session_complete = False
            if all_read:
                delete_ids = [
                    int(item["message_id"])
                    for item in items
                    if item.get("message_id") is not None
                ]
                model.current_batch = []
                if progress.last_ayah_number >= int(model.target_ayah_number or 0):
                    model.status = "complete"
                    model.mode = None
                    model.target_ayah_number = None
                    model.prompt_message_id = None
                    model.expires_at = None
                    session_complete = True
                    scope = await self._repository.scope(session, scope_id)
                    local_date = now.astimezone(ZoneInfo(scope.timezone)).date()  # type: ignore[union-attr]
                    await self._repository.add_daily_stat(
                        session,
                        scope_id=scope_id,
                        local_date=local_date,
                        sessions=1,
                    )
            else:
                model.current_batch = items
            model.last_activity_at = now
            if not session_complete:
                model.expires_at = now + SESSION_TIMEOUT
            return ReadUpdate(
                session=self._session_value(model),
                clicked_item=clicked,
                delete_message_ids=delete_ids,
                batch_complete=all_read,
                session_complete=session_complete,
            )

    async def cancel_session(self, scope_id: int, session_id: int) -> list[int]:
        async with self._database.transaction() as session:
            model = await self._repository.session_model(
                session, scope_id, for_update=True
            )
            self._require_session(model, session_id)
            ids = self._session_message_ids(model)
            self._expire_session(model, status="cancelled")
            return ids

    async def expire_sessions(self) -> list[tuple[int, list[int]]]:
        expired: list[tuple[int, list[int]]] = []
        async with self._database.transaction() as session:
            models = await self._repository.expired_sessions(session, utc_now())
            for model in models:
                scope = await self._repository.scope(session, model.scope_id)
                if scope is not None:
                    expired.append((scope.chat_id, self._session_message_ids(model)))
                self._expire_session(model, status="expired")
        return expired

    async def stats(self, scope_id: int) -> StatsValue:
        async with self._database.transaction() as session:
            scope = await self._repository.scope(session, scope_id)
            if scope is None:
                raise IslamicInputError("Scope chat tidak ditemukan.")
            today = utc_now().astimezone(ZoneInfo(scope.timezone)).date()
            progress = await self._repository.progress(session, scope_id)
            recent = await self._repository.stats_since(
                session, scope_id, today - timedelta(days=29)
            )
            all_rows = await self._repository.all_stats(session, scope_id)
        by_date = {row.local_date: row.ayahs_read for row in recent}
        active_dates = [row.local_date for row in all_rows if row.ayahs_read > 0]
        return StatsValue(
            progress=self._progress_value(progress),
            today=by_date.get(today, 0),
            seven_days=sum(
                count
                for day, count in by_date.items()
                if day >= today - timedelta(days=6)
            ),
            thirty_days=sum(by_date.values()),
            sessions_completed=sum(row.sessions_completed for row in all_rows),
            current_streak=self._current_streak(active_dates, today),
            longest_streak=self._longest_streak(active_dates),
            last_activity_at=progress.last_activity_at,
        )

    @staticmethod
    def _scope_value(model: Any) -> ScopeValue:
        return ScopeValue(
            id=model.id,
            bot_id=model.bot_id,
            chat_id=model.chat_id,
            chat_type=model.chat_type,
            configured=model.configured,
            latitude=model.latitude,
            longitude=model.longitude,
            city=model.city,
            country=model.country,
            timezone=model.timezone,
            calculation_method=model.calculation_method,
            active_reminder_message_id=model.active_reminder_message_id,
            setup_state=model.setup_state,
            setup_data=dict(model.setup_data),
        )

    @staticmethod
    def _progress_value(model: Any) -> ProgressValue:
        return ProgressValue(
            last_ayah_number=model.last_ayah_number,
            last_surah_number=model.last_surah_number,
            last_surah_name=model.last_surah_name,
            last_ayah_in_surah=model.last_ayah_in_surah,
            last_page=model.last_page,
        )

    @staticmethod
    def _session_value(model: QuranSessionModel) -> SessionValue:
        return SessionValue(
            id=model.id,
            scope_id=model.scope_id,
            status=model.status,
            mode=model.mode,
            target_ayah_number=model.target_ayah_number,
            current_batch=[dict(item) for item in model.current_batch],
            prompt_message_id=model.prompt_message_id,
            expires_at=model.expires_at,
        )

    @staticmethod
    def _require_session(
        model: QuranSessionModel | None, session_id: int, *, active: bool = False
    ) -> None:
        if model is None or model.id != session_id:
            raise IslamicInputError("Sesi baca tidak ditemukan.")
        valid = ("active",) if active else ("awaiting_mode", "active")
        if model.status not in valid or model.expires_at is None or model.expires_at <= utc_now():
            raise IslamicInputError("Sesi baca sudah berakhir.")

    @staticmethod
    def _apply_ayah(progress: Any, item: dict[str, Any]) -> None:
        progress.last_ayah_number = int(item["number"])
        progress.last_surah_number = int(item["surah_number"])
        progress.last_surah_name = str(item["surah_name"])
        progress.last_ayah_in_surah = int(item["number_in_surah"])
        progress.last_page = int(item["page"])

    @staticmethod
    def _session_message_ids(model: QuranSessionModel) -> list[int]:
        ids = [
            int(item["message_id"])
            for item in model.current_batch
            if item.get("message_id") is not None
        ]
        if model.prompt_message_id is not None:
            ids.append(model.prompt_message_id)
        return ids

    @staticmethod
    def _expire_session(model: QuranSessionModel, *, status: str) -> None:
        model.status = status
        model.mode = None
        model.target_ayah_number = None
        model.current_batch = []
        model.prompt_message_id = None
        model.expires_at = None

    @staticmethod
    def _current_streak(days: Sequence[date], today: date) -> int:
        values = set(days)
        cursor = today if today in values else today - timedelta(days=1)
        streak = 0
        while cursor in values:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    @staticmethod
    def _longest_streak(days: Sequence[date]) -> int:
        longest = current = 0
        previous: date | None = None
        for day in sorted(set(days)):
            current = current + 1 if previous and day == previous + timedelta(days=1) else 1
            longest = max(longest, current)
            previous = day
        return longest


class IslamicScheduler:
    def __init__(
        self,
        service: IslamicService,
        deliver: Callable[[PrayerClaim], Awaitable[None]],
        cleanup: Callable[[int, list[int]], Awaitable[None]],
    ) -> None:
        self._service = service
        self._deliver = deliver
        self._cleanup = cleanup
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="islamic-scheduler")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                for claim in await self._service.claim_due_prayers():
                    try:
                        await self._deliver(claim)
                    except Exception as error:
                        await self._service.release_prayer_claim(claim)
                        await logger.aexception(
                            "islamic_reminder_delivery_failed",
                            scope_id=claim.scope_id,
                            kind=claim.kind,
                            error_type=type(error).__name__,
                        )
                for chat_id, message_ids in await self._service.expire_sessions():
                    await self._cleanup(chat_id, message_ids)
                await self._service.sync_due_calendars()
            except Exception as error:
                await logger.aexception(
                    "islamic_scheduler_tick_failed", error_type=type(error).__name__
                )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=30)
            except TimeoutError:
                pass
