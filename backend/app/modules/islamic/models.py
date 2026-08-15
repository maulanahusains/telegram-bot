from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class IslamicScopeModel(TimestampMixin, Base):
    __tablename__ = "islamic_scopes"
    __table_args__ = (
        UniqueConstraint("bot_id", "chat_id", name="uq_islamic_scope_bot_chat"),
        Index("ix_islamic_scope_bot_configured", "bot_id", "configured"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_bots.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_type: Mapped[str] = mapped_column(String(32), nullable=False)
    configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    city: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Jakarta"
    )
    calculation_method: Mapped[int | None] = mapped_column(Integer)
    reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    active_reminder_message_id: Mapped[int | None] = mapped_column(BigInteger)
    setup_state: Mapped[str | None] = mapped_column(String(64))
    setup_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    last_calendar_check_date: Mapped[date | None] = mapped_column(Date)


class PrayerScheduleModel(TimestampMixin, Base):
    __tablename__ = "islamic_prayer_schedules"
    __table_args__ = (
        UniqueConstraint(
            "scope_id", "local_date", "prayer_name", name="uq_prayer_scope_date_name"
        ),
        Index("ix_prayer_due", "adhan_at", "quran_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_id: Mapped[int] = mapped_column(
        ForeignKey("islamic_scopes.id", ondelete="CASCADE"), nullable=False
    )
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    prayer_name: Mapped[str] = mapped_column(String(16), nullable=False)
    adhan_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pre_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    adhan_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    quran_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    claimed_kind: Mapped[str | None] = mapped_column(String(16))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuranProgressModel(TimestampMixin, Base):
    __tablename__ = "islamic_quran_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_id: Mapped[int] = mapped_column(
        ForeignKey("islamic_scopes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    last_ayah_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_surah_number: Mapped[int | None] = mapped_column(Integer)
    last_surah_name: Mapped[str | None] = mapped_column(String(128))
    last_ayah_in_surah: Mapped[int | None] = mapped_column(Integer)
    last_page: Mapped[int | None] = mapped_column(Integer)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuranSessionModel(TimestampMixin, Base):
    __tablename__ = "islamic_quran_sessions"
    __table_args__ = (Index("ix_quran_session_expiry", "status", "expires_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_id: Mapped[int] = mapped_column(
        ForeignKey("islamic_scopes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="idle")
    mode: Mapped[str | None] = mapped_column(String(16))
    target_ayah_number: Mapped[int | None] = mapped_column(Integer)
    current_batch: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    prompt_message_id: Mapped[int | None] = mapped_column(BigInteger)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuranDailyStatModel(TimestampMixin, Base):
    __tablename__ = "islamic_quran_daily_stats"
    __table_args__ = (
        UniqueConstraint("scope_id", "local_date", name="uq_quran_stat_scope_date"),
        Index("ix_quran_stat_scope_date", "scope_id", "local_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_id: Mapped[int] = mapped_column(
        ForeignKey("islamic_scopes.id", ondelete="CASCADE"), nullable=False
    )
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    ayahs_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sessions_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
