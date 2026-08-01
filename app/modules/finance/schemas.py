from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum


class FinanceCommand(StrEnum):
    START = "/start"
    HELP = "/help"
    SETUP = "/setup"
    BUDGET = "/budget"
    SPEND = "/spend"
    TRANSACTIONS = "/transactions"
    EDIT = "/edit"
    DELETE = "/delete"
    SUMMARY = "/summary"
    HISTORY = "/history"
    ALERT = "/alert"
    TIMEZONE = "/timezone"
    CANCEL = "/cancel"


@dataclass(frozen=True, slots=True)
class SetupInput:
    amount: int
    first_days: int
    recurring_days: int
    start_date: date


@dataclass(frozen=True, slots=True)
class SpendInput:
    amount: int
    purpose: str
    spent_on: date | None


@dataclass(frozen=True, slots=True)
class ProfileValue:
    id: int
    bot_user_id: int
    base_budget: int
    recurring_days: int
    timezone: str
    alert_enabled: bool
    alert_time: time
    alert_chat_id: int


@dataclass(frozen=True, slots=True)
class PeriodValue:
    id: int
    sequence: int
    start_date: date
    end_date: date
    base_budget: int
    previous_balance: int | None
    applied_carry: int | None
    effective_budget: int | None
    rollover_status: str
    realization: int


@dataclass(frozen=True, slots=True)
class TransactionValue:
    id: int
    amount: int
    purpose: str
    spent_on: date


@dataclass(frozen=True, slots=True)
class AlertClaim:
    profile: ProfileValue
    period: PeriodValue
    local_date: date
