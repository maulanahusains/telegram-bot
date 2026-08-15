from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class LifeProfileInput(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
    display_name: str | None = Field(default=None, max_length=255)
    height_cm: Decimal | None = Field(default=None, gt=30, le=300, max_digits=5, decimal_places=2)
    sex: Literal["female", "male", "other", "prefer_not_to_say"] | None = None

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class LifeProfileValue(LifeProfileInput):
    id: int
    created_at: datetime
    updated_at: datetime


class NutritionGoalInput(BaseModel):
    calorie_target_kcal: int = Field(gt=0, le=20_000)
    protein_min_g: Decimal = Field(ge=0, le=2_000, max_digits=7, decimal_places=2)
    protein_max_g: Decimal = Field(ge=0, le=2_000, max_digits=7, decimal_places=2)
    effective_from: date

    @model_validator(mode="after")
    def validate_protein_range(self) -> "NutritionGoalInput":
        if self.protein_max_g < self.protein_min_g:
            raise ValueError("protein_max_g must be at least protein_min_g")
        return self


class NutritionGoalValue(NutritionGoalInput):
    id: int
    created_at: datetime
    updated_at: datetime


class DestinationCandidateValue(BaseModel):
    id: int
    bot_name: str
    kind: Literal["private", "group", "supergroup"]
    chat_label: str
    last_seen_at: datetime


class DestinationActivationInput(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    make_default: bool = False

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class DestinationPatch(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None
    is_default: bool | None = None

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class NotificationDestinationValue(BaseModel):
    id: int
    bot_name: str
    kind: Literal["private", "group", "supergroup"]
    label: str
    enabled: bool
    is_default: bool
    verified_at: datetime | None
    disabled_reason: str | None
    created_at: datetime
    updated_at: datetime


class RecurrenceRule(BaseModel):
    frequency: Literal["daily", "weekly"]
    time: time
    weekdays: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_weekdays(self) -> "RecurrenceRule":
        if self.frequency == "weekly" and not self.weekdays:
            raise ValueError("weekly recurrence requires at least one weekday")
        if self.frequency == "daily" and self.weekdays:
            raise ValueError("daily recurrence cannot set weekdays")
        if len(set(self.weekdays)) != len(self.weekdays):
            raise ValueError("weekdays must be unique")
        return self


class ReminderInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    kind: Literal["reminder", "routine", "meal", "workout"] = "reminder"
    schedule_type: Literal["one_time", "recurring"]
    scheduled_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    recurrence: RecurrenceRule | None = None
    destination_id: int = Field(gt=0)
    enabled: bool = True

    @field_validator("title", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized:
            return normalized
        raise ValueError("text must not be blank")

    @model_validator(mode="after")
    def validate_schedule(self) -> "ReminderInput":
        if self.schedule_type == "one_time":
            if self.scheduled_at is None or self.recurrence is not None:
                raise ValueError("one-time reminders require scheduled_at only")
            if self.scheduled_at.tzinfo is None:
                raise ValueError("scheduled_at must include a timezone offset")
        elif self.recurrence is None or self.scheduled_at is not None:
            raise ValueError("recurring reminders require recurrence only")
        return self


class ReminderPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    kind: Literal["reminder", "routine", "meal", "workout"] | None = None
    schedule_type: Literal["one_time", "recurring"] | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    recurrence: RecurrenceRule | None = None
    destination_id: int | None = Field(default=None, gt=0)
    enabled: bool | None = None


class ReminderValue(BaseModel):
    id: int
    title: str
    notes: str | None
    kind: Literal["reminder", "routine", "meal", "workout"]
    schedule_type: Literal["one_time", "recurring"]
    scheduled_at: datetime | None
    timezone: str
    recurrence: RecurrenceRule | None
    destination_id: int
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReminderOccurrenceValue(BaseModel):
    id: int
    reminder_id: int
    scheduled_for: datetime
    status: Literal["pending", "claimed", "sent", "failed", "missed", "completed", "skipped"]
    attempts: int
    delivered_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
