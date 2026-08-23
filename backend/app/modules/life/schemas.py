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


GoalDirection = Literal["lose_weight", "maintain_weight", "gain_weight"]


class GoalPreferenceInput(BaseModel):
    goal_direction: GoalDirection
    desired_weekly_change_kg: Decimal | None = Field(
        default=None,
        ge=-5,
        le=5,
        max_digits=6,
        decimal_places=3,
    )

    @model_validator(mode="after")
    def validate_direction(self) -> "GoalPreferenceInput":
        desired = self.desired_weekly_change_kg
        if desired is None:
            return self
        if self.goal_direction == "lose_weight" and desired > 0:
            raise ValueError("lose_weight requires a non-positive weekly change")
        if self.goal_direction == "maintain_weight" and desired != 0:
            raise ValueError("maintain_weight requires a zero weekly change")
        if self.goal_direction == "gain_weight" and desired < 0:
            raise ValueError("gain_weight requires a non-negative weekly change")
        return self


class GoalPreferenceValue(GoalPreferenceInput):
    id: int
    last_evaluated_on: date | None
    created_at: datetime
    updated_at: datetime


class GoalRecommendationValue(BaseModel):
    id: int
    status: Literal["pending", "applied", "dismissed", "expired", "superseded"]
    delivery_status: Literal["pending", "sent", "failed"]
    current_goal_id: int | None
    current_calorie_target_kcal: int
    recommended_calorie_target_kcal: int
    goal_direction: GoalDirection
    desired_weekly_change_kg: Decimal | None
    window_start: date
    window_end: date
    observation_count: int
    trend_kg_per_week: Decimal
    rule_version: str
    rule_snapshot: dict[str, object]
    offered_at: datetime
    expires_at: datetime
    decided_at: datetime | None


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
    kind: Literal["reminder", "routine", "meal", "workout", "grocery", "goal_recommendation"] = "reminder"
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
    kind: Literal["reminder", "routine", "meal", "workout", "grocery", "goal_recommendation"] | None = None
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
    kind: Literal["reminder", "routine", "meal", "workout", "grocery", "goal_recommendation"]
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


class FoodInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    serving_label: str = Field(min_length=1, max_length=128)
    serving_grams: Decimal | None = Field(default=None, gt=0, le=10_000, max_digits=8, decimal_places=2)
    calories_kcal: int = Field(ge=0, le=100_000)
    protein_g: Decimal = Field(ge=0, le=10_000, max_digits=8, decimal_places=2)
    active: bool = True

    @field_validator("name", "serving_label")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class FoodPatch(FoodInput):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    serving_label: str | None = Field(default=None, min_length=1, max_length=128)
    calories_kcal: int | None = Field(default=None, ge=0, le=100_000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=10_000, max_digits=8, decimal_places=2)


class FoodValue(FoodInput):
    id: int
    created_at: datetime
    updated_at: datetime


class MealTemplateItemInput(BaseModel):
    food_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, le=10_000, max_digits=8, decimal_places=2)


class MealTemplateInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    meal_slot: str | None = Field(default=None, max_length=64)
    active: bool = True
    items: list[MealTemplateItemInput] = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_template_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class MealTemplatePatch(MealTemplateInput):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    items: list[MealTemplateItemInput] | None = Field(default=None, min_length=1, max_length=50)


class MealTemplateItemValue(MealTemplateItemInput):
    id: int
    position: int
    food_name: str


class MealTemplateValue(BaseModel):
    id: int
    name: str
    meal_slot: str | None
    active: bool
    items: list[MealTemplateItemValue]
    created_at: datetime
    updated_at: datetime


class MealLogItemInput(BaseModel):
    food_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, le=10_000, max_digits=8, decimal_places=2)


class MealLogInput(BaseModel):
    meal_slot: str | None = Field(default=None, max_length=64)
    status: Literal["logged", "planned", "skipped"] = "logged"
    consumed_at: datetime
    note: str | None = Field(default=None, max_length=1000)
    items: list[MealLogItemInput] = Field(min_length=1, max_length=50)

    @field_validator("consumed_at")
    @classmethod
    def require_aware_consumed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("consumed_at must include a timezone offset")
        return value


class MealLogItemValue(BaseModel):
    id: int
    food_id: int | None
    food_name: str
    quantity: Decimal
    calories_kcal: int
    protein_g: Decimal
    position: int


class MealLogValue(BaseModel):
    id: int
    meal_slot: str | None
    status: Literal["logged", "planned", "skipped"]
    consumed_at: datetime
    local_date: date
    note: str | None
    items: list[MealLogItemValue]
    calories_kcal: int
    protein_g: Decimal
    created_at: datetime
    updated_at: datetime


class WeightLogInput(BaseModel):
    weighed_at: datetime
    weight_kg: Decimal = Field(gt=0, le=500, max_digits=6, decimal_places=2)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("weighed_at")
    @classmethod
    def require_aware_weighed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("weighed_at must include a timezone offset")
        return value


class WeightLogValue(WeightLogInput):
    id: int
    local_date: date
    created_at: datetime
    updated_at: datetime


class WorkoutScheduleInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    workout_type: str | None = Field(default=None, max_length=128)
    reminder: ReminderInput

    @model_validator(mode="after")
    def validate_workout_reminder(self) -> "WorkoutScheduleInput":
        if self.reminder.kind != "workout":
            self.reminder.kind = "workout"
        return self


class WorkoutSchedulePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    workout_type: str | None = Field(default=None, max_length=128)
    enabled: bool | None = None
    reminder: ReminderPatch | None = None


class WorkoutScheduleValue(BaseModel):
    id: int
    name: str
    workout_type: str | None
    enabled: bool
    reminder: ReminderValue
    created_at: datetime
    updated_at: datetime


class WorkoutCompletionInput(BaseModel):
    status: Literal["done", "skipped"]
    note: str | None = Field(default=None, max_length=1000)


class WorkoutCompletionValue(BaseModel):
    id: int
    workout_schedule_id: int
    occurrence_id: int
    scheduled_for: datetime
    status: Literal["done", "skipped"]
    completed_at: datetime | None
    note: str | None


class TodayValue(BaseModel):
    date: date
    timezone: str
    calorie_target_kcal: int | None
    protein_min_g: Decimal | None
    protein_max_g: Decimal | None
    calories_consumed: int
    protein_consumed: Decimal
    meals: list[MealLogValue]
    workout: WorkoutScheduleValue | None
    workout_occurrence_id: int | None
    workout_completion: WorkoutCompletionValue | None
    upcoming_reminders: list[ReminderValue]


class ProgressDayValue(BaseModel):
    date: date
    calories_consumed: int
    calorie_target_kcal: int | None
    protein_consumed: Decimal
    protein_min_g: Decimal | None
    workout_done: int
    workout_skipped: int


class ProgressValue(BaseModel):
    start_date: date
    end_date: date
    days: list[ProgressDayValue]
    weights: list[WeightLogValue]


GroceryCadence = Literal["weekly", "monthly", "custom"]


class GroceryListInput(BaseModel):
    name: str = Field(default="Weekly shopping", min_length=1, max_length=255)
    cadence: GroceryCadence = "weekly"
    starts_on: date | None = None
    ends_on: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "GroceryListInput":
        if self.cadence == "custom" and (self.starts_on is None or self.ends_on is None):
            raise ValueError("starts_on and ends_on are required for custom cadence")
        if self.cadence != "custom" and (self.starts_on is not None or self.ends_on is not None):
            raise ValueError("starts_on and ends_on are only allowed for custom cadence")
        if self.starts_on is not None and self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("ends_on must not precede starts_on")
        return self


class GroceryListState(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    cadence: GroceryCadence
    starts_on: date
    ends_on: date
    status: Literal["active", "archived"]

    @model_validator(mode="after")
    def validate_dates(self) -> "GroceryListState":
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on must not precede starts_on")
        return self


class GroceryListPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    cadence: GroceryCadence | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    status: Literal["active", "archived"] | None = None


class GroceryItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=0, le=100_000, max_digits=8, decimal_places=2)
    unit: str = Field(min_length=1, max_length=64)
    estimated_unit_price_rupiah: int | None = Field(default=None, ge=0, le=2_000_000_000)


class GroceryItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    quantity: Decimal | None = Field(default=None, gt=0, le=100_000, max_digits=8, decimal_places=2)
    unit: str | None = Field(default=None, min_length=1, max_length=64)
    estimated_unit_price_rupiah: int | None = Field(default=None, ge=0, le=2_000_000_000)
    is_bought: bool | None = None


class GroceryItemValue(BaseModel):
    id: int
    name: str
    quantity: Decimal
    unit: str
    estimated_unit_price_rupiah: int | None
    estimated_total_rupiah: int | None
    is_bought: bool
    bought_at: datetime | None
    position: int


class GroceryListValue(BaseModel):
    id: int
    name: str
    cadence: GroceryCadence
    starts_on: date
    ends_on: date
    status: Literal["active", "archived"]
    items: list[GroceryItemValue]
    estimated_total_rupiah: int
    created_at: datetime
    updated_at: datetime


class RecurringGroceryItemInput(GroceryItemInput):
    enabled: bool = True


class RecurringGroceryItemPatch(RecurringGroceryItemInput):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    quantity: Decimal | None = Field(default=None, gt=0, le=100_000, max_digits=8, decimal_places=2)
    unit: str | None = Field(default=None, min_length=1, max_length=64)
    estimated_unit_price_rupiah: int | None = Field(default=None, ge=0, le=2_000_000_000)


class RecurringGroceryItemValue(BaseModel):
    id: int
    name: str
    quantity: Decimal
    unit: str
    estimated_unit_price_rupiah: int | None
    enabled: bool
