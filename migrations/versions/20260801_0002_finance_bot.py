"""Create finance bot tables.

Revision ID: 20260801_0002
Revises: 20260731_0001
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0002"
down_revision: str | None = "20260731_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "finance_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_user_id",
            sa.Integer(),
            sa.ForeignKey("bot_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("base_budget", sa.BigInteger(), nullable=False),
        sa.Column("recurring_days", sa.SmallInteger(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("alert_enabled", sa.Boolean(), nullable=False),
        sa.Column("alert_time", sa.Time(), nullable=False),
        sa.Column("alert_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("last_alert_local_date", sa.Date()),
        sa.Column("alert_claimed_local_date", sa.Date()),
        sa.Column("alert_claimed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "base_budget >= 0", name="ck_finance_profiles_base_budget_non_negative"
        ),
        sa.CheckConstraint(
            "recurring_days BETWEEN 1 AND 365",
            name="ck_finance_profiles_recurring_days_valid",
        ),
        sa.UniqueConstraint(
            "bot_user_id", name="uq_finance_profiles_bot_user_id"
        ),
    )

    op.create_table(
        "finance_budget_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("finance_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("base_budget", sa.BigInteger(), nullable=False),
        sa.Column("previous_balance", sa.BigInteger()),
        sa.Column("applied_carry", sa.BigInteger()),
        sa.Column("effective_budget", sa.BigInteger()),
        sa.Column("rollover_status", sa.String(length=32), nullable=False),
        sa.Column("rollover_decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_finance_budget_periods_date_range_valid",
        ),
        sa.CheckConstraint(
            "base_budget >= 0",
            name="ck_finance_budget_periods_base_budget_non_negative",
        ),
        sa.UniqueConstraint(
            "profile_id",
            "sequence",
            name="uq_finance_period_profile_sequence",
        ),
        sa.UniqueConstraint(
            "profile_id",
            "start_date",
            name="uq_finance_period_profile_start",
        ),
    )
    op.create_index(
        "ix_finance_period_profile_dates",
        "finance_budget_periods",
        ["profile_id", "start_date", "end_date"],
    )

    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("finance_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "period_id",
            sa.Integer(),
            sa.ForeignKey("finance_budget_periods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_update_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=False),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "amount > 0", name="ck_finance_transactions_amount_positive"
        ),
        sa.UniqueConstraint(
            "profile_id",
            "source_update_id",
            name="uq_finance_tx_profile_update",
        ),
    )
    op.create_index(
        "ix_finance_tx_period_date",
        "finance_transactions",
        ["period_id", "spent_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_finance_tx_period_date", table_name="finance_transactions")
    op.drop_table("finance_transactions")
    op.drop_index(
        "ix_finance_period_profile_dates", table_name="finance_budget_periods"
    )
    op.drop_table("finance_budget_periods")
    op.drop_table("finance_profiles")
