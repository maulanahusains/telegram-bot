"""Create Life nutrition, weight, and fitness records.

Revision ID: 20260816_0007
Revises: 20260816_0006
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0007"
down_revision: str | None = "20260816_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("life_foods", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("serving_label", sa.String(128), nullable=False), sa.Column("serving_grams", sa.Numeric(8, 2)), sa.Column("calories_kcal", sa.Integer(), nullable=False), sa.Column("protein_g", sa.Numeric(8, 2), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("owner_user_id", "name", name="uq_life_food_owner_name"), sa.CheckConstraint("calories_kcal >= 0", name="ck_life_food_calories"), sa.CheckConstraint("protein_g >= 0", name="ck_life_food_protein"), sa.CheckConstraint("serving_grams IS NULL OR serving_grams > 0", name="ck_life_food_serving_grams"))
    op.create_index("ix_life_food_owner_active", "life_foods", ["owner_user_id", "active"])
    op.create_table("life_meal_templates", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("meal_slot", sa.String(64)), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_life_meal_template_owner_active", "life_meal_templates", ["owner_user_id", "active"])
    op.create_table("life_meal_template_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("template_id", sa.Integer(), sa.ForeignKey("life_meal_templates.id", ondelete="CASCADE"), nullable=False), sa.Column("food_id", sa.Integer(), sa.ForeignKey("life_foods.id", ondelete="RESTRICT"), nullable=False), sa.Column("quantity", sa.Numeric(8, 2), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.UniqueConstraint("template_id", "position", name="uq_life_meal_template_item_position"), sa.CheckConstraint("quantity > 0", name="ck_life_meal_template_item_quantity"))
    op.create_index("ix_life_meal_template_item_template", "life_meal_template_items", ["template_id", "position"])
    op.create_table("life_meal_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("meal_slot", sa.String(64)), sa.Column("status", sa.String(16), nullable=False, server_default="logged"), sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("local_date", sa.Date(), nullable=False), sa.Column("note", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.CheckConstraint("status IN ('logged', 'planned', 'skipped')", name="ck_life_meal_log_status"))
    op.create_index("ix_life_meal_log_owner_local_date", "life_meal_logs", ["owner_user_id", "local_date"])
    op.create_table("life_meal_log_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("meal_log_id", sa.Integer(), sa.ForeignKey("life_meal_logs.id", ondelete="CASCADE"), nullable=False), sa.Column("food_id", sa.Integer(), sa.ForeignKey("life_foods.id", ondelete="SET NULL")), sa.Column("food_name", sa.String(255), nullable=False), sa.Column("quantity", sa.Numeric(8, 2), nullable=False), sa.Column("calories_kcal", sa.Integer(), nullable=False), sa.Column("protein_g", sa.Numeric(8, 2), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.CheckConstraint("quantity > 0", name="ck_life_meal_log_item_quantity"), sa.CheckConstraint("calories_kcal >= 0", name="ck_life_meal_log_item_calories"), sa.CheckConstraint("protein_g >= 0", name="ck_life_meal_log_item_protein"))
    op.create_index("ix_life_meal_log_item_log", "life_meal_log_items", ["meal_log_id", "position"])
    op.create_table("life_weight_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("weighed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("local_date", sa.Date(), nullable=False), sa.Column("weight_kg", sa.Numeric(6, 2), nullable=False), sa.Column("note", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("owner_user_id", "local_date", name="uq_life_weight_owner_local_date"), sa.CheckConstraint("weight_kg > 0 AND weight_kg <= 500", name="ck_life_weight_range"))
    op.create_index("ix_life_weight_owner_local_date", "life_weight_logs", ["owner_user_id", "local_date"])
    op.create_table("life_workout_schedules", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("reminder_id", sa.Integer(), sa.ForeignKey("life_reminders.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("workout_type", sa.String(128)), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_life_workout_owner_enabled", "life_workout_schedules", ["owner_user_id", "enabled"])
    op.create_table("life_workout_completions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("workout_schedule_id", sa.Integer(), sa.ForeignKey("life_workout_schedules.id", ondelete="CASCADE"), nullable=False), sa.Column("occurrence_id", sa.Integer(), sa.ForeignKey("life_reminder_occurrences.id", ondelete="CASCADE"), nullable=False), sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("note", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("occurrence_id", name="uq_life_workout_completion_occurrence"), sa.CheckConstraint("status IN ('done', 'skipped')", name="ck_life_workout_completion_status"))
    op.create_index("ix_life_workout_completion_schedule_time", "life_workout_completions", ["workout_schedule_id", "scheduled_for"])


def downgrade() -> None:
    for index, table in (("ix_life_workout_completion_schedule_time", "life_workout_completions"), ("ix_life_workout_owner_enabled", "life_workout_schedules"), ("ix_life_weight_owner_local_date", "life_weight_logs"), ("ix_life_meal_log_item_log", "life_meal_log_items"), ("ix_life_meal_log_owner_local_date", "life_meal_logs"), ("ix_life_meal_template_item_template", "life_meal_template_items"), ("ix_life_meal_template_owner_active", "life_meal_templates"), ("ix_life_food_owner_active", "life_foods")):
        op.drop_index(index, table_name=table)
    for table in ("life_workout_completions", "life_workout_schedules", "life_weight_logs", "life_meal_log_items", "life_meal_logs", "life_meal_template_items", "life_meal_templates", "life_foods"):
        op.drop_table(table)
