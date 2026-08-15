"""Create Life profile, goals, and notification destinations.

Revision ID: 20260816_0005
Revises: 20260815_0004
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0005"
down_revision: str | None = "20260815_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "life_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255)),
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2)),
        sa.Column("sex", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "life_nutrition_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calorie_target_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_min_g", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("protein_max_g", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("calorie_target_kcal > 0", name="ck_life_goal_calories_positive"),
        sa.CheckConstraint("protein_min_g >= 0", name="ck_life_goal_protein_min"),
        sa.CheckConstraint("protein_max_g >= protein_min_g", name="ck_life_goal_protein_range"),
        sa.UniqueConstraint("owner_user_id", "effective_from", name="uq_life_goal_owner_effective"),
    )
    op.create_index("ix_life_goal_owner_effective", "life_nutrition_goals", ["owner_user_id", "effective_from"])
    op.create_table(
        "life_destination_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("telegram_chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_user_id", "bot_id", "telegram_chat_id", name="uq_life_destination_candidate_owner_bot_chat"),
    )
    op.create_index("ix_life_destination_candidate_owner_seen", "life_destination_candidates", ["owner_user_id", "last_seen_at"])
    op.create_table(
        "life_notification_destinations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("telegram_chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=255)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("disabled_reason", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_user_id", "bot_id", "telegram_chat_id", name="uq_life_destination_owner_bot_chat"),
    )
    op.create_index("ix_life_destination_owner_enabled", "life_notification_destinations", ["owner_user_id", "enabled"])
    op.create_index("ix_life_destination_bot_chat", "life_notification_destinations", ["bot_id", "telegram_chat_id"])
    op.create_index("uq_life_destination_owner_default", "life_notification_destinations", ["owner_user_id"], unique=True, postgresql_where=sa.text("is_default = true"))


def downgrade() -> None:
    op.drop_index("uq_life_destination_owner_default", table_name="life_notification_destinations")
    op.drop_index("ix_life_destination_bot_chat", table_name="life_notification_destinations")
    op.drop_index("ix_life_destination_owner_enabled", table_name="life_notification_destinations")
    op.drop_table("life_notification_destinations")
    op.drop_index("ix_life_destination_candidate_owner_seen", table_name="life_destination_candidates")
    op.drop_table("life_destination_candidates")
    op.drop_index("ix_life_goal_owner_effective", table_name="life_nutrition_goals")
    op.drop_table("life_nutrition_goals")
    op.drop_table("life_profiles")
