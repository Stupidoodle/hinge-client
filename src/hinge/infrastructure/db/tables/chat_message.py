"""Hinge chat message table definition."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
)

from hinge.infrastructure.db.metadata import metadata

hinge_chat_message_table = Table(
    "hinge_chat_messages",
    metadata,
    Column("message_id", Integer, primary_key=True),
    Column(
        "channel_url",
        String,
        ForeignKey("hinge_chat_channels.channel_url", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("sender_sendbird_id", String, nullable=False),
    Column("is_from_me", Boolean, nullable=False, default=False),
    Column("message_type", String, nullable=False, default=""),
    Column("body", String, nullable=False, default=""),
    Column("data", String, nullable=False, default=""),
    Column("custom_type", String, nullable=False, default=""),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime),
    Column("dedup_id", String),
    Column("attempt_id", String),
    Column("is_match_message", Boolean, nullable=False, default=False),
    Column("origin", String),
    Column("sent_from_app_version", String),
    Column("sent_from_platform", String),
    Column("file_url", String),
    Column("file_type", String),
    Column("file_size", Integer),
    Column("file_name", String),
    Column("is_removed", Boolean, nullable=False, default=False),
    Column("is_silent", Boolean, nullable=False, default=False),
    Column("is_op_msg", Boolean, nullable=False, default=False),
    Column("message_survival_seconds", Integer, nullable=False, default=0),
    Column("message_retention_hour", Integer, nullable=False, default=0),
    Column("raw_json", String, nullable=False, default=""),
    Index(
        "ix_hinge_chat_messages_channel_created",
        "channel_url",
        "created_at",
    ),
)
