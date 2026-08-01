from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.islamic.models import (
    IslamicScopeModel,
    PrayerScheduleModel,
    QuranDailyStatModel,
    QuranProgressModel,
    QuranSessionModel,
)
from app.modules.islamic.schemas import PrayerTimeValue


class IslamicRepository:
    async def get_or_create_scope(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        chat_id: int,
        chat_type: str,
    ) -> IslamicScopeModel:
        model = await session.scalar(
            insert(IslamicScopeModel)
            .values(bot_id=bot_id, chat_id=chat_id, chat_type=chat_type)
            .on_conflict_do_update(
                constraint="uq_islamic_scope_bot_chat",
                set_={"chat_type": chat_type},
            )
            .returning(IslamicScopeModel)
        )
        if model is None:
            raise RuntimeError("Islamic scope upsert failed")
        return model

    async def scope(
        self, session: AsyncSession, scope_id: int, *, for_update: bool = False
    ) -> IslamicScopeModel | None:
        statement = select(IslamicScopeModel).where(IslamicScopeModel.id == scope_id)
        if for_update:
            statement = statement.with_for_update(of=IslamicScopeModel)
        return await session.scalar(statement)

    async def scope_by_chat(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        chat_id: int,
        for_update: bool = False,
    ) -> IslamicScopeModel | None:
        statement = select(IslamicScopeModel).where(
            IslamicScopeModel.bot_id == bot_id,
            IslamicScopeModel.chat_id == chat_id,
        )
        if for_update:
            statement = statement.with_for_update(of=IslamicScopeModel)
        return await session.scalar(statement)

    async def configured_scopes(
        self, session: AsyncSession, bot_id: int
    ) -> Sequence[IslamicScopeModel]:
        result = await session.scalars(
            select(IslamicScopeModel).where(
                IslamicScopeModel.bot_id == bot_id,
                IslamicScopeModel.configured.is_(True),
                IslamicScopeModel.reminders_enabled.is_(True),
            )
        )
        return result.all()

    async def delete_future_prayers(
        self, session: AsyncSession, scope_id: int, from_date: date
    ) -> None:
        await session.execute(
            delete(PrayerScheduleModel).where(
                PrayerScheduleModel.scope_id == scope_id,
                PrayerScheduleModel.local_date >= from_date,
            )
        )

    async def upsert_prayers(
        self,
        session: AsyncSession,
        scope_id: int,
        prayers: Sequence[PrayerTimeValue],
    ) -> None:
        now = datetime.now(timezone.utc)
        for prayer in prayers:
            pre_status = "skipped" if now >= prayer.adhan_at else "pending"
            adhan_status = (
                "skipped"
                if now > prayer.adhan_at + timedelta(minutes=5)
                else "pending"
            )
            quran_status = (
                "skipped"
                if now > prayer.quran_at + timedelta(minutes=60)
                else "pending"
            )
            await session.execute(
                insert(PrayerScheduleModel)
                .values(
                    scope_id=scope_id,
                    local_date=prayer.local_date,
                    prayer_name=prayer.prayer_name,
                    adhan_at=prayer.adhan_at,
                    quran_at=prayer.quran_at,
                    pre_status=pre_status,
                    adhan_status=adhan_status,
                    quran_status=quran_status,
                )
                .on_conflict_do_nothing(
                    constraint="uq_prayer_scope_date_name"
                )
            )

    async def prayer_count(
        self, session: AsyncSession, scope_id: int, start: date, end: date
    ) -> int:
        value = await session.scalar(
            select(func.count(PrayerScheduleModel.id)).where(
                PrayerScheduleModel.scope_id == scope_id,
                PrayerScheduleModel.local_date >= start,
                PrayerScheduleModel.local_date <= end,
            )
        )
        return int(value or 0)

    async def due_prayers(
        self, session: AsyncSession, *, now: datetime, limit: int = 100
    ) -> Sequence[PrayerScheduleModel]:
        result = await session.scalars(
            select(PrayerScheduleModel)
            .where(
                or_(
                    PrayerScheduleModel.pre_status == "pending",
                    PrayerScheduleModel.adhan_status == "pending",
                    PrayerScheduleModel.quran_status == "pending",
                ),
                PrayerScheduleModel.adhan_at <= now + timedelta(minutes=15),
                or_(
                    PrayerScheduleModel.claimed_kind.is_(None),
                    PrayerScheduleModel.claimed_at < now - timedelta(minutes=5),
                ),
            )
            .order_by(PrayerScheduleModel.adhan_at, PrayerScheduleModel.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.all()

    async def progress(
        self, session: AsyncSession, scope_id: int, *, for_update: bool = False
    ) -> QuranProgressModel:
        statement = select(QuranProgressModel).where(
            QuranProgressModel.scope_id == scope_id
        )
        if for_update:
            statement = statement.with_for_update(of=QuranProgressModel)
        model = await session.scalar(statement)
        if model is None:
            await session.execute(
                insert(QuranProgressModel)
                .values(scope_id=scope_id)
                .on_conflict_do_nothing(index_elements=[QuranProgressModel.scope_id])
            )
            statement = select(QuranProgressModel).where(
                QuranProgressModel.scope_id == scope_id
            )
            if for_update:
                statement = statement.with_for_update(of=QuranProgressModel)
            model = await session.scalar(statement)
            if model is None:
                raise RuntimeError("Quran progress upsert failed")
        return model

    async def get_or_create_session(
        self, session: AsyncSession, scope_id: int
    ) -> QuranSessionModel:
        await session.execute(
            insert(QuranSessionModel)
            .values(scope_id=scope_id)
            .on_conflict_do_nothing(index_elements=[QuranSessionModel.scope_id])
        )
        model = await session.scalar(
            select(QuranSessionModel)
            .where(QuranSessionModel.scope_id == scope_id)
            .with_for_update(of=QuranSessionModel)
        )
        if model is None:
            raise RuntimeError("Quran session upsert failed")
        return model

    async def session_model(
        self, session: AsyncSession, scope_id: int, *, for_update: bool = False
    ) -> QuranSessionModel | None:
        statement = select(QuranSessionModel).where(
            QuranSessionModel.scope_id == scope_id
        )
        if for_update:
            statement = statement.with_for_update(of=QuranSessionModel)
        return await session.scalar(statement)

    async def expired_sessions(
        self, session: AsyncSession, now: datetime
    ) -> Sequence[QuranSessionModel]:
        result = await session.scalars(
            select(QuranSessionModel)
            .where(
                QuranSessionModel.status.in_(("awaiting_mode", "active")),
                QuranSessionModel.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
        return result.all()

    async def add_daily_stat(
        self,
        session: AsyncSession,
        *,
        scope_id: int,
        local_date: date,
        ayahs: int = 0,
        sessions: int = 0,
    ) -> None:
        await session.execute(
            insert(QuranDailyStatModel)
            .values(
                scope_id=scope_id,
                local_date=local_date,
                ayahs_read=ayahs,
                sessions_completed=sessions,
            )
            .on_conflict_do_update(
                constraint="uq_quran_stat_scope_date",
                set_={
                    "ayahs_read": QuranDailyStatModel.ayahs_read + ayahs,
                    "sessions_completed": QuranDailyStatModel.sessions_completed
                    + sessions,
                },
            )
        )

    async def stats_since(
        self, session: AsyncSession, scope_id: int, since: date
    ) -> Sequence[QuranDailyStatModel]:
        result = await session.scalars(
            select(QuranDailyStatModel)
            .where(
                QuranDailyStatModel.scope_id == scope_id,
                QuranDailyStatModel.local_date >= since,
            )
            .order_by(QuranDailyStatModel.local_date)
        )
        return result.all()

    async def all_stats(
        self, session: AsyncSession, scope_id: int
    ) -> Sequence[QuranDailyStatModel]:
        result = await session.scalars(
            select(QuranDailyStatModel)
            .where(QuranDailyStatModel.scope_id == scope_id)
            .order_by(QuranDailyStatModel.local_date)
        )
        return result.all()
