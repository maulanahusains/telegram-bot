"""Add deterministic weight-trend calorie recommendations."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260823_0011"
down_revision: str | None = "20260823_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "life_goal_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("goal_direction", sa.String(length=16), nullable=False),
        sa.Column("desired_weekly_change_kg", sa.Numeric(6, 3), nullable=True),
        sa.Column("last_evaluated_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("goal_direction IN ('lose_weight', 'maintain_weight', 'gain_weight')", name="ck_life_goal_preference_direction"),
        sa.CheckConstraint("desired_weekly_change_kg IS NULL OR desired_weekly_change_kg >= -5 AND desired_weekly_change_kg <= 5", name="ck_life_goal_preference_weekly_change"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["telegram_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", name="uq_life_goal_preference_owner"),
    )
    op.create_table(
        "life_goal_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("current_goal_id", sa.Integer(), nullable=True),
        sa.Column("current_calorie_target_kcal", sa.Integer(), nullable=False),
        sa.Column("recommended_calorie_target_kcal", sa.Integer(), nullable=False),
        sa.Column("goal_direction", sa.String(length=16), nullable=False),
        sa.Column("desired_weekly_change_kg", sa.Numeric(6, 3), nullable=True),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("trend_kg_per_week", sa.Numeric(8, 4), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("rule_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_message_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'applied', 'dismissed', 'expired', 'superseded')", name="ck_life_goal_recommendation_status"),
        sa.CheckConstraint("delivery_status IN ('pending', 'sent', 'failed')", name="ck_life_goal_recommendation_delivery_status"),
        sa.CheckConstraint("current_calorie_target_kcal > 0 AND current_calorie_target_kcal <= 20000", name="ck_life_goal_recommendation_current_target"),
        sa.CheckConstraint("recommended_calorie_target_kcal > 0 AND recommended_calorie_target_kcal <= 20000", name="ck_life_goal_recommendation_recommended_target"),
        sa.CheckConstraint("goal_direction IN ('lose_weight', 'maintain_weight', 'gain_weight')", name="ck_life_goal_recommendation_direction"),
        sa.CheckConstraint("desired_weekly_change_kg IS NULL OR desired_weekly_change_kg >= -5 AND desired_weekly_change_kg <= 5", name="ck_life_goal_recommendation_weekly_change"),
        sa.ForeignKeyConstraint(["current_goal_id"], ["life_nutrition_goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["telegram_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_life_goal_recommendation_owner_status_created",
        "life_goal_recommendations",
        ["owner_user_id", "status", sa.text("created_at DESC")],
    )
    op.create_index(
        "uq_life_goal_recommendation_one_pending",
        "life_goal_recommendations",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.add_column(
        "life_reminders",
        sa.Column("goal_recommendation_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_life_reminders_goal_rec",
        "life_reminders",
        "life_goal_recommendations",
        ["goal_recommendation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_life_reminders_goal_recommendation_id",
        "life_reminders",
        ["goal_recommendation_id"],
    )
    op.drop_constraint("ck_life_reminder_kind", "life_reminders", type_="check")
    op.create_check_constraint(
        "ck_life_reminder_kind",
        "life_reminders",
        "kind IN ('reminder', 'routine', 'meal', 'workout', 'grocery', 'goal_recommendation')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_life_reminder_kind", "life_reminders", type_="check")
    op.create_check_constraint(
        "ck_life_reminder_kind",
        "life_reminders",
        "kind IN ('reminder', 'routine', 'meal', 'workout', 'grocery')",
    )
    op.drop_constraint("uq_life_reminders_goal_recommendation_id", "life_reminders", type_="unique")
    op.drop_constraint(
        "fk_life_reminders_goal_rec",
        "life_reminders",
        type_="foreignkey",
    )
    op.drop_column("life_reminders", "goal_recommendation_id")
    op.drop_index("uq_life_goal_recommendation_one_pending", table_name="life_goal_recommendations")
    op.drop_index("ix_life_goal_recommendation_owner_status_created", table_name="life_goal_recommendations")
    op.drop_table("life_goal_recommendations")
    op.drop_table("life_goal_preferences")
