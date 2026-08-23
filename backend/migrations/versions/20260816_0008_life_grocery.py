"""Create Life grocery lists and recurring items.

Revision ID: 20260816_0008
Revises: 20260816_0007
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0008"
down_revision: str | None = "20260816_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("life_grocery_lists", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("starts_on", sa.Date(), nullable=False), sa.Column("ends_on", sa.Date(), nullable=False), sa.Column("status", sa.String(16), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.CheckConstraint("status IN ('active', 'archived')", name="ck_life_grocery_list_status"), sa.CheckConstraint("ends_on >= starts_on", name="ck_life_grocery_list_dates"))
    op.create_index("ix_life_grocery_list_owner_dates", "life_grocery_lists", ["owner_user_id", "starts_on", "ends_on"])
    op.create_table("life_grocery_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("list_id", sa.Integer(), sa.ForeignKey("life_grocery_lists.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("quantity", sa.Numeric(8, 2), nullable=False), sa.Column("unit", sa.String(64), nullable=False), sa.Column("estimated_unit_price_rupiah", sa.Integer()), sa.Column("is_bought", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("bought_at", sa.DateTime(timezone=True)), sa.Column("position", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("list_id", "position", name="uq_life_grocery_item_position"), sa.CheckConstraint("quantity > 0", name="ck_life_grocery_item_quantity"), sa.CheckConstraint("estimated_unit_price_rupiah IS NULL OR estimated_unit_price_rupiah >= 0", name="ck_life_grocery_item_price"))
    op.create_index("ix_life_grocery_item_list_bought", "life_grocery_items", ["list_id", "is_bought"])
    op.create_table("life_recurring_grocery_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("quantity", sa.Numeric(8, 2), nullable=False), sa.Column("unit", sa.String(64), nullable=False), sa.Column("estimated_unit_price_rupiah", sa.Integer()), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.CheckConstraint("quantity > 0", name="ck_life_recurring_grocery_quantity"), sa.CheckConstraint("estimated_unit_price_rupiah IS NULL OR estimated_unit_price_rupiah >= 0", name="ck_life_recurring_grocery_price"))
    op.create_index("ix_life_recurring_grocery_owner_enabled", "life_recurring_grocery_items", ["owner_user_id", "enabled"])


def downgrade() -> None:
    op.drop_index("ix_life_recurring_grocery_owner_enabled", table_name="life_recurring_grocery_items")
    op.drop_table("life_recurring_grocery_items")
    op.drop_index("ix_life_grocery_item_list_bought", table_name="life_grocery_items")
    op.drop_table("life_grocery_items")
    op.drop_index("ix_life_grocery_list_owner_dates", table_name="life_grocery_lists")
    op.drop_table("life_grocery_lists")
