from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
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


class LifeGoalPreferenceModel(TimestampMixin, Base):
    __tablename__ = "life_goal_preferences"
    __table_args__ = (
        UniqueConstraint("owner_user_id", name="uq_life_goal_preference_owner"),
        CheckConstraint("goal_direction IN ('lose_weight', 'maintain_weight', 'gain_weight')", name="ck_life_goal_preference_direction"),
        CheckConstraint("desired_weekly_change_kg IS NULL OR desired_weekly_change_kg >= -5 AND desired_weekly_change_kg <= 5", name="ck_life_goal_preference_weekly_change"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    goal_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    desired_weekly_change_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    last_evaluated_on: Mapped[date | None] = mapped_column(Date)


class LifeGoalRecommendationModel(TimestampMixin, Base):
    __tablename__ = "life_goal_recommendations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'applied', 'dismissed', 'expired', 'superseded')", name="ck_life_goal_recommendation_status"),
        CheckConstraint("delivery_status IN ('pending', 'sent', 'failed')", name="ck_life_goal_recommendation_delivery_status"),
        CheckConstraint("current_calorie_target_kcal > 0 AND current_calorie_target_kcal <= 20000", name="ck_life_goal_recommendation_current_target"),
        CheckConstraint("recommended_calorie_target_kcal > 0 AND recommended_calorie_target_kcal <= 20000", name="ck_life_goal_recommendation_recommended_target"),
        CheckConstraint("goal_direction IN ('lose_weight', 'maintain_weight', 'gain_weight')", name="ck_life_goal_recommendation_direction"),
        CheckConstraint("desired_weekly_change_kg IS NULL OR desired_weekly_change_kg >= -5 AND desired_weekly_change_kg <= 5", name="ck_life_goal_recommendation_weekly_change"),
        Index("ix_life_goal_recommendation_owner_status_created", "owner_user_id", "status", text("created_at DESC")),
        Index("uq_life_goal_recommendation_one_pending", "owner_user_id", unique=True, postgresql_where=text("status = 'pending'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    current_goal_id: Mapped[int | None] = mapped_column(ForeignKey("life_nutrition_goals.id", ondelete="SET NULL"))
    current_calorie_target_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_calorie_target_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    goal_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    desired_weekly_change_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trend_kg_per_week: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)


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
        CheckConstraint("kind IN ('reminder', 'routine', 'meal', 'workout', 'grocery', 'goal_recommendation')", name="ck_life_reminder_kind"),
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
    one_time_grace_seconds: Mapped[int | None] = mapped_column(Integer)
    goal_recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("life_goal_recommendations.id", ondelete="SET NULL"), unique=True)
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


class LifeFoodModel(TimestampMixin, Base):
    __tablename__ = "life_foods"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_life_food_owner_name"),
        CheckConstraint("calories_kcal >= 0", name="ck_life_food_calories"),
        CheckConstraint("protein_g >= 0", name="ck_life_food_protein"),
        CheckConstraint("serving_grams IS NULL OR serving_grams > 0", name="ck_life_food_serving_grams"),
        Index("ix_life_food_owner_active", "owner_user_id", "active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    serving_label: Mapped[str] = mapped_column(String(128), nullable=False)
    serving_grams: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    calories_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LifeMealTemplateModel(TimestampMixin, Base):
    __tablename__ = "life_meal_templates"
    __table_args__ = (Index("ix_life_meal_template_owner_active", "owner_user_id", "active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    meal_slot: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LifeMealTemplateItemModel(Base):
    __tablename__ = "life_meal_template_items"
    __table_args__ = (
        UniqueConstraint("template_id", "position", name="uq_life_meal_template_item_position"),
        CheckConstraint("quantity > 0", name="ck_life_meal_template_item_quantity"),
        Index("ix_life_meal_template_item_template", "template_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("life_meal_templates.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[int] = mapped_column(ForeignKey("life_foods.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class LifeMealLogModel(TimestampMixin, Base):
    __tablename__ = "life_meal_logs"
    __table_args__ = (
        CheckConstraint("status IN ('logged', 'planned', 'skipped')", name="ck_life_meal_log_status"),
        Index("ix_life_meal_log_owner_local_date", "owner_user_id", "local_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    meal_slot: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="logged")
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000))


class LifeMealLogItemModel(Base):
    __tablename__ = "life_meal_log_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_life_meal_log_item_quantity"),
        CheckConstraint("calories_kcal >= 0", name="ck_life_meal_log_item_calories"),
        CheckConstraint("protein_g >= 0", name="ck_life_meal_log_item_protein"),
        Index("ix_life_meal_log_item_log", "meal_log_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_log_id: Mapped[int] = mapped_column(ForeignKey("life_meal_logs.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[int | None] = mapped_column(ForeignKey("life_foods.id", ondelete="SET NULL"))
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    calories_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class LifeWeightLogModel(TimestampMixin, Base):
    __tablename__ = "life_weight_logs"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "local_date", name="uq_life_weight_owner_local_date"),
        CheckConstraint("weight_kg > 0 AND weight_kg <= 500", name="ck_life_weight_range"),
        Index("ix_life_weight_owner_local_date", "owner_user_id", "local_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    weighed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000))


class LifeWorkoutScheduleModel(TimestampMixin, Base):
    __tablename__ = "life_workout_schedules"
    __table_args__ = (Index("ix_life_workout_owner_enabled", "owner_user_id", "enabled"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    reminder_id: Mapped[int] = mapped_column(ForeignKey("life_reminders.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workout_type: Mapped[str | None] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LifeWorkoutCompletionModel(TimestampMixin, Base):
    __tablename__ = "life_workout_completions"
    __table_args__ = (
        UniqueConstraint("occurrence_id", name="uq_life_workout_completion_occurrence"),
        CheckConstraint("status IN ('done', 'skipped')", name="ck_life_workout_completion_status"),
        Index("ix_life_workout_completion_schedule_time", "workout_schedule_id", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_schedule_id: Mapped[int] = mapped_column(ForeignKey("life_workout_schedules.id", ondelete="CASCADE"), nullable=False)
    occurrence_id: Mapped[int] = mapped_column(ForeignKey("life_reminder_occurrences.id", ondelete="CASCADE"), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(1000))


class LifeGroceryListModel(TimestampMixin, Base):
    __tablename__ = "life_grocery_lists"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_life_grocery_list_status"),
        CheckConstraint("cadence IN ('weekly', 'monthly', 'custom')", name="ck_life_grocery_list_cadence"),
        CheckConstraint("ends_on >= starts_on", name="ck_life_grocery_list_dates"),
        Index("ix_life_grocery_list_owner_dates", "owner_user_id", "starts_on", "ends_on"),
        Index("ix_life_grocery_list_rotation", "status", "cadence", "ends_on"),
        Index("uq_life_grocery_list_one_active_per_owner", "owner_user_id", unique=True, postgresql_where=text("status = 'active'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    unbought_reminder_id: Mapped[int | None] = mapped_column(ForeignKey("life_reminders.id", ondelete="SET NULL"), unique=True)


class LifeGroceryItemModel(TimestampMixin, Base):
    __tablename__ = "life_grocery_items"
    __table_args__ = (
        UniqueConstraint("list_id", "position", name="uq_life_grocery_item_position"),
        CheckConstraint("quantity > 0", name="ck_life_grocery_item_quantity"),
        CheckConstraint("estimated_unit_price_rupiah IS NULL OR estimated_unit_price_rupiah >= 0", name="ck_life_grocery_item_price"),
        Index("ix_life_grocery_item_list_bought", "list_id", "is_bought"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("life_grocery_lists.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_unit_price_rupiah: Mapped[int | None] = mapped_column(Integer)
    is_bought: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bought_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class LifeRecurringGroceryItemModel(TimestampMixin, Base):
    __tablename__ = "life_recurring_grocery_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_life_recurring_grocery_quantity"),
        CheckConstraint("estimated_unit_price_rupiah IS NULL OR estimated_unit_price_rupiah >= 0", name="ck_life_recurring_grocery_price"),
        Index("ix_life_recurring_grocery_owner_enabled", "owner_user_id", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_unit_price_rupiah: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
