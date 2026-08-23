"""Add grocery list cadence and enforce one active list per owner.

Revision ID: 20260823_0009
Revises: 20260816_0008
Create Date: 2026-08-23

Existing lists are backfilled as ``custom`` because their original scheduling
intent is unknown. Before the partial unique index is created, duplicate active
lists are resolved deterministically: the newest list by ``created_at`` (then
highest ``id``) remains active and all older active lists are archived.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0009"
down_revision: str | None = "20260816_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("life_grocery_lists", sa.Column("cadence", sa.String(16), nullable=True))
    op.execute(
        sa.text(
            "UPDATE life_grocery_lists "
            "SET cadence = 'custom' "
            "WHERE cadence IS NULL"
        )
    )
    op.alter_column("life_grocery_lists", "cadence", nullable=False)
    op.create_check_constraint(
        "ck_life_grocery_list_cadence",
        "life_grocery_lists",
        "cadence IN ('weekly', 'monthly', 'custom')",
    )
    op.execute(
        sa.text(
            "WITH ranked_active AS ("
            "SELECT id, ROW_NUMBER() OVER ("
            "PARTITION BY owner_user_id "
            "ORDER BY created_at DESC, id DESC"
            ") AS row_number "
            "FROM life_grocery_lists "
            "WHERE status = 'active'"
            ") "
            "UPDATE life_grocery_lists AS grocery_list "
            "SET status = 'archived' "
            "FROM ranked_active "
            "WHERE grocery_list.id = ranked_active.id "
            "AND ranked_active.row_number > 1"
        )
    )
    op.create_index(
        "uq_life_grocery_list_one_active_per_owner",
        "life_grocery_lists",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_life_grocery_list_one_active_per_owner",
        table_name="life_grocery_lists",
    )
    op.drop_constraint(
        "ck_life_grocery_list_cadence",
        "life_grocery_lists",
        type_="check",
    )
    op.drop_column("life_grocery_lists", "cadence")
