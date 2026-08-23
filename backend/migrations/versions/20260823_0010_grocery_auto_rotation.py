"""Add grocery auto-rotation and durable unbought reminders.

Revision ID: 20260823_0010
Revises: 20260823_0009
Create Date: 2026-08-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0010"
down_revision: str | None = "20260823_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "life_reminders",
        sa.Column("one_time_grace_seconds", sa.Integer(), nullable=True),
    )
    op.drop_constraint(
        "ck_life_reminder_kind",
        "life_reminders",
        type_="check",
    )
    op.create_check_constraint(
        "ck_life_reminder_kind",
        "life_reminders",
        "kind IN ('reminder', 'routine', 'meal', 'workout', 'grocery')",
    )
    op.add_column(
        "life_grocery_lists",
        sa.Column("unbought_reminder_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_life_grocery_lists_unbought_reminder_id_life_reminders",
        "life_grocery_lists",
        "life_reminders",
        ["unbought_reminder_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_life_grocery_lists_unbought_reminder_id",
        "life_grocery_lists",
        ["unbought_reminder_id"],
    )
    op.create_index(
        "ix_life_grocery_list_rotation",
        "life_grocery_lists",
        ["status", "cadence", "ends_on"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_life_grocery_list_rotation",
        table_name="life_grocery_lists",
    )
    op.drop_constraint(
        "uq_life_grocery_lists_unbought_reminder_id",
        "life_grocery_lists",
        type_="unique",
    )
    op.drop_constraint(
        "fk_life_grocery_lists_unbought_reminder_id_life_reminders",
        "life_grocery_lists",
        type_="foreignkey",
    )
    op.drop_column("life_grocery_lists", "unbought_reminder_id")
    op.drop_constraint("ck_life_reminder_kind", "life_reminders", type_="check")
    op.create_check_constraint(
        "ck_life_reminder_kind",
        "life_reminders",
        "kind IN ('reminder', 'routine', 'meal', 'workout')",
    )
    op.drop_column("life_reminders", "one_time_grace_seconds")
