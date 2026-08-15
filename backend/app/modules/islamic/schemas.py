from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


class IslamicInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AyahValue:
    number: int
    surah_number: int
    surah_name: str
    number_in_surah: int
    page: int

    def as_batch_item(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "surah_number": self.surah_number,
            "surah_name": self.surah_name,
            "number_in_surah": self.number_in_surah,
            "page": self.page,
            "message_id": None,
            "read": False,
        }


@dataclass(frozen=True, slots=True)
class ScopeValue:
    id: int
    bot_id: int
    chat_id: int
    chat_type: str
    configured: bool
    latitude: float | None
    longitude: float | None
    city: str | None
    country: str | None
    timezone: str
    calculation_method: int | None
    active_reminder_message_id: int | None
    setup_state: str | None
    setup_data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PrayerTimeValue:
    local_date: date
    prayer_name: str
    adhan_at: datetime
    quran_at: datetime


@dataclass(frozen=True, slots=True)
class PrayerClaim:
    schedule_id: int
    scope_id: int
    chat_id: int
    prayer_name: str
    kind: str
    old_message_id: int | None
    skip_message: bool = False


@dataclass(frozen=True, slots=True)
class ProgressValue:
    last_ayah_number: int
    last_surah_number: int | None
    last_surah_name: str | None
    last_ayah_in_surah: int | None
    last_page: int | None


@dataclass(frozen=True, slots=True)
class SessionValue:
    id: int
    scope_id: int
    status: str
    mode: str | None
    target_ayah_number: int | None
    current_batch: list[dict[str, Any]]
    prompt_message_id: int | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReadUpdate:
    session: SessionValue
    clicked_item: dict[str, Any] | None
    delete_message_ids: list[int]
    batch_complete: bool
    session_complete: bool


@dataclass(frozen=True, slots=True)
class StatsValue:
    progress: ProgressValue
    today: int
    seven_days: int
    thirty_days: int
    sessions_completed: int
    current_streak: int
    longest_streak: int
    last_activity_at: datetime | None
