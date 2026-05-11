"""Hinge chat channel table definition."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Table,
)

from hinge.infrastructure.db.metadata import metadata

hinge_chat_channel_table = Table(
    "hinge_chat_channels",
    metadata,
    Column("channel_url", String, primary_key=True),
    Column("subject_id", String),
    Column("counterparty_sendbird_id", String, nullable=False),
    Column("is_connection_active", Boolean, nullable=False, default=True),
    Column("is_match_message", Boolean, nullable=False, default=False),
    Column("inviter_user_id", String),
    Column("created_by_user_id", String),
    Column("custom_type", String, nullable=False, default=""),
    Column("disappearing_message_seconds", Integer, nullable=False, default=0),
    Column("disappearing_triggered_by_read", Boolean, nullable=False, default=False),
    Column("sms_fallback_wait_seconds", Integer, nullable=False, default=0),
    Column("count_preference", String, nullable=False, default=""),
    Column("push_trigger_option", String, nullable=False, default=""),
    Column("has_ai_bot", Boolean, nullable=False, default=False),
    Column("has_bot", Boolean, nullable=False, default=False),
    Column("is_ai_agent_channel", Boolean, nullable=False, default=False),
    Column("ignore_profanity_filter", Boolean, nullable=False, default=False),
    Column("unread_count", Integer, nullable=False, default=0),
    Column("last_message_id", Integer),
    Column("last_message_at", DateTime),
    Column("channel_created_at", DateTime, nullable=False),
    Column("first_synced_at", DateTime, nullable=False),
    Column("last_synced_at", DateTime, nullable=False),
    Column("raw_json", String, nullable=False, default=""),
    Index("ix_hinge_chat_channels_last_message_at", "last_message_at"),
)
