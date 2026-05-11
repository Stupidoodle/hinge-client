"""add hinge chat tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11 00:00:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "hinge_chat_channels",
        sa.Column("channel_url", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=True),
        sa.Column("counterparty_sendbird_id", sa.String(), nullable=False),
        sa.Column("is_connection_active", sa.Boolean(), nullable=False),
        sa.Column("is_match_message", sa.Boolean(), nullable=False),
        sa.Column("inviter_user_id", sa.String(), nullable=True),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("custom_type", sa.String(), nullable=False),
        sa.Column("disappearing_message_seconds", sa.Integer(), nullable=False),
        sa.Column("disappearing_triggered_by_read", sa.Boolean(), nullable=False),
        sa.Column("sms_fallback_wait_seconds", sa.Integer(), nullable=False),
        sa.Column("count_preference", sa.String(), nullable=False),
        sa.Column("push_trigger_option", sa.String(), nullable=False),
        sa.Column("has_ai_bot", sa.Boolean(), nullable=False),
        sa.Column("has_bot", sa.Boolean(), nullable=False),
        sa.Column("is_ai_agent_channel", sa.Boolean(), nullable=False),
        sa.Column("ignore_profanity_filter", sa.Boolean(), nullable=False),
        sa.Column("unread_count", sa.Integer(), nullable=False),
        sa.Column("last_message_id", sa.Integer(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("channel_created_at", sa.DateTime(), nullable=False),
        sa.Column("first_synced_at", sa.DateTime(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=False),
        sa.Column("raw_json", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("channel_url"),
    )
    op.create_index(
        op.f("ix_hinge_chat_channels_last_message_at"),
        "hinge_chat_channels",
        ["last_message_at"],
        unique=False,
    )
    op.create_table(
        "hinge_chat_messages",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("channel_url", sa.String(), nullable=False),
        sa.Column("sender_sendbird_id", sa.String(), nullable=False),
        sa.Column("is_from_me", sa.Boolean(), nullable=False),
        sa.Column("message_type", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("data", sa.String(), nullable=False),
        sa.Column("custom_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("dedup_id", sa.String(), nullable=True),
        sa.Column("attempt_id", sa.String(), nullable=True),
        sa.Column("is_match_message", sa.Boolean(), nullable=False),
        sa.Column("origin", sa.String(), nullable=True),
        sa.Column("sent_from_app_version", sa.String(), nullable=True),
        sa.Column("sent_from_platform", sa.String(), nullable=True),
        sa.Column("file_url", sa.String(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("is_removed", sa.Boolean(), nullable=False),
        sa.Column("is_silent", sa.Boolean(), nullable=False),
        sa.Column("is_op_msg", sa.Boolean(), nullable=False),
        sa.Column("message_survival_seconds", sa.Integer(), nullable=False),
        sa.Column("message_retention_hour", sa.Integer(), nullable=False),
        sa.Column("raw_json", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["channel_url"],
            ["hinge_chat_channels.channel_url"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_index(
        op.f("ix_hinge_chat_messages_channel_created"),
        "hinge_chat_messages",
        ["channel_url", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_hinge_chat_messages_channel_created"),
        table_name="hinge_chat_messages",
    )
    op.drop_table("hinge_chat_messages")
    op.drop_index(
        op.f("ix_hinge_chat_channels_last_message_at"),
        table_name="hinge_chat_channels",
    )
    op.drop_table("hinge_chat_channels")
