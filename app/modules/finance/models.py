from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class RolloverStatus(StrEnum):
    INITIAL = "initial"
    PENDING = "pending"
    CARRY = "carry"
    BASE = "base"
    ZERO = "zero"
    CUSTOM = "custom"
    AUTO_BASE = "auto_base"


class FinanceProfileModel(TimestampMixin, Base):
    __tablename__ = "finance_profiles"
    __table_args__ = (
        CheckConstraint("base_budget >= 0", name="base_budget_non_negative"),
        CheckConstraint(
            "recurring_days BETWEEN 1 AND 365",
            name="recurring_days_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_user_id: Mapped[int] = mapped_column(
        ForeignKey("bot_users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    base_budget: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recurring_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=7)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Jakarta"
    )
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_time: Mapped[time] = mapped_column(
        Time(timezone=False), nullable=False, default=time(8, 0)
    )
    alert_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_alert_local_date: Mapped[date | None] = mapped_column(Date)
    alert_claimed_local_date: Mapped[date | None] = mapped_column(Date)
    alert_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinanceBudgetPeriodModel(TimestampMixin, Base):
    __tablename__ = "finance_budget_periods"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "sequence", name="uq_finance_period_profile_sequence"
        ),
        UniqueConstraint(
            "profile_id", "start_date", name="uq_finance_period_profile_start"
        ),
        CheckConstraint("end_date >= start_date", name="date_range_valid"),
        CheckConstraint("base_budget >= 0", name="base_budget_non_negative"),
        Index("ix_finance_period_profile_dates", "profile_id", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("finance_profiles.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_budget: Mapped[int] = mapped_column(BigInteger, nullable=False)
    previous_balance: Mapped[int | None] = mapped_column(BigInteger)
    applied_carry: Mapped[int | None] = mapped_column(BigInteger)
    effective_budget: Mapped[int | None] = mapped_column(BigInteger)
    rollover_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=RolloverStatus.PENDING.value
    )
    rollover_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinanceTransactionModel(TimestampMixin, Base):
    __tablename__ = "finance_transactions"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "source_update_id", name="uq_finance_tx_profile_update"
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_finance_tx_period_date", "period_id", "spent_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("finance_profiles.id", ondelete="CASCADE"), nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("finance_budget_periods.id", ondelete="CASCADE"), nullable=False
    )
    source_update_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
