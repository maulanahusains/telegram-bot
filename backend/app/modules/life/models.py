from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class LifeProfileModel(TimestampMixin, Base):
    __tablename__ = "life_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    sex: Mapped[str | None] = mapped_column(String(32))


class LifeNutritionGoalModel(TimestampMixin, Base):
    __tablename__ = "life_nutrition_goals"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "effective_from", name="uq_life_goal_owner_effective"),
        CheckConstraint("calorie_target_kcal > 0", name="ck_life_goal_calories_positive"),
        CheckConstraint("protein_min_g >= 0", name="ck_life_goal_protein_min"),
        CheckConstraint("protein_max_g >= protein_min_g", name="ck_life_goal_protein_range"),
        Index("ix_life_goal_owner_effective", "owner_user_id", "effective_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    calorie_target_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_min_g: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    protein_max_g: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)


class LifeDestinationCandidateModel(TimestampMixin, Base):
    """Webhook-observed owner/chat evidence; it is not a destination itself."""

    __tablename__ = "life_destination_candidates"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "bot_id", "telegram_chat_id", name="uq_life_destination_candidate_owner_bot_chat"),
        Index("ix_life_destination_candidate_owner_seen", "owner_user_id", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    bot_id: Mapped[int] = mapped_column(ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LifeNotificationDestinationModel(TimestampMixin, Base):
    __tablename__ = "life_notification_destinations"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "bot_id", "telegram_chat_id", name="uq_life_destination_owner_bot_chat"),
        Index("ix_life_destination_owner_enabled", "owner_user_id", "enabled"),
        Index("ix_life_destination_bot_chat", "bot_id", "telegram_chat_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    bot_id: Mapped[int] = mapped_column(ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="RESTRICT"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_reason: Mapped[str | None] = mapped_column(String(128))


class LifeReminderModel(TimestampMixin, Base):
    __tablename__ = "life_reminders"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_life_reminder_title"),
        CheckConstraint("schedule_type IN ('one_time', 'recurring')", name="ck_life_reminder_schedule_type"),
        CheckConstraint("kind IN ('reminder', 'routine', 'meal', 'workout')", name="ck_life_reminder_kind"),
        Index("ix_life_reminder_due", "enabled", "next_run_at"),
        Index("ix_life_reminder_owner_due", "owner_user_id", "enabled", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    destination_id: Mapped[int] = mapped_column(ForeignKey("life_notification_destinations.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000))
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="reminder")
    schedule_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    recurrence: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LifeReminderOccurrenceModel(TimestampMixin, Base):
    __tablename__ = "life_reminder_occurrences"
    __table_args__ = (
        UniqueConstraint("reminder_id", "scheduled_for", name="uq_life_occurrence_reminder_scheduled"),
        CheckConstraint("status IN ('pending', 'claimed', 'sent', 'failed', 'missed', 'completed', 'skipped')", name="ck_life_occurrence_status"),
        Index("ix_life_occurrence_due", "status", "available_at"),
        Index("ix_life_occurrence_lease", "status", "lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reminder_id: Mapped[int] = mapped_column(ForeignKey("life_reminders.id", ondelete="CASCADE"), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claim_token: Mapped[str | None] = mapped_column(String(64))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    failure_detail: Mapped[str | None] = mapped_column(String(255))
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)
