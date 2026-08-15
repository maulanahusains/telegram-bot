"""Create platform and sample bot tables.

Revision ID: 20260731_0001
Revises:
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260731_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

bot_user_status = postgresql.ENUM(
    "active", "blocked", "disabled", name="bot_user_status", create_type=False
)
update_status = postgresql.ENUM(
    "received",
    "processing",
    "processed",
    "failed",
    name="telegram_update_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    bot_user_status.create(bind, checkfirst=True)
    update_status.create(bind, checkfirst=True)

    op.create_table(
        "telegram_bots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("token_ciphertext", sa.Text(), nullable=False),
        sa.Column("secret_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text()),
        sa.Column("module_name", sa.String(length=64), nullable=False),
        sa.Column("webhook_url", sa.Text()),
        sa.Column("webhook_sync_fingerprint", sa.String(length=64)),
        sa.Column("webhook_synced_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint("name", name="uq_telegram_bots_name"),
    )
    op.create_index("ix_telegram_bots_enabled", "telegram_bots", ["enabled"])

    op.create_table(
        "telegram_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255)),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255)),
        sa.Column("language_code", sa.String(length=16)),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.UniqueConstraint(
            "telegram_user_id", name="uq_telegram_users_telegram_user_id"
        ),
    )

    op.create_table(
        "telegram_chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255)),
        sa.Column("username", sa.String(length=255)),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.UniqueConstraint(
            "telegram_chat_id", name="uq_telegram_chats_telegram_chat_id"
        ),
    )

    op.create_table(
        "bot_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_id",
            sa.Integer(),
            sa.ForeignKey("telegram_bots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("telegram_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            bot_user_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column("role", sa.String(length=64), nullable=False, server_default="user"),
        sa.Column("locale", sa.String(length=16)),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.UniqueConstraint(
            "bot_id", "user_id", name="uq_bot_users_bot_id_user_id"
        ),
    )
    op.create_index("ix_bot_users_bot_status", "bot_users", ["bot_id", "status"])

    op.create_table(
        "bot_user_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_user_id",
            sa.Integer(),
            sa.ForeignKey("bot_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=128)),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint(
            "bot_user_id", name="uq_bot_user_states_bot_user_id"
        ),
    )

    op.create_table(
        "telegram_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_id",
            sa.Integer(),
            sa.ForeignKey("telegram_bots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger()),
        sa.Column("chat_id", sa.BigInteger()),
        sa.Column("update_type", sa.String(length=64), nullable=False),
        sa.Column("status", update_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.UniqueConstraint(
            "bot_id", "update_id", name="uq_telegram_updates_bot_update"
        ),
    )
    op.create_index(
        "ix_telegram_updates_status_lease",
        "telegram_updates",
        ["status", "lease_expires_at"],
    )

    op.create_table(
        "sample_user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_user_id",
            sa.Integer(),
            sa.ForeignKey("bot_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_command_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.UniqueConstraint(
            "bot_user_id", name="uq_sample_user_profiles_bot_user_id"
        ),
    )


def downgrade() -> None:
    op.drop_table("sample_user_profiles")
    op.drop_index(
        "ix_telegram_updates_status_lease", table_name="telegram_updates"
    )
    op.drop_table("telegram_updates")
    op.drop_table("bot_user_states")
    op.drop_index("ix_bot_users_bot_status", table_name="bot_users")
    op.drop_table("bot_users")
    op.drop_table("telegram_chats")
    op.drop_table("telegram_users")
    op.drop_index("ix_telegram_bots_enabled", table_name="telegram_bots")
    op.drop_table("telegram_bots")
    update_status.drop(op.get_bind(), checkfirst=True)
    bot_user_status.drop(op.get_bind(), checkfirst=True)

