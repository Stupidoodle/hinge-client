"""Hinge chat channel domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class HingeChatChannel:
    """Sendbird chat channel for a Hinge match."""

    channel_url: str
    counterparty_sendbird_id: str
    custom_type: str
    channel_created_at: datetime
    subject_id: str | None = None
    is_connection_active: bool = True
    is_match_message: bool = False
    inviter_user_id: str | None = None
    created_by_user_id: str | None = None
    disappearing_message_seconds: int = 0
    disappearing_triggered_by_read: bool = False
    sms_fallback_wait_seconds: int = 0
    count_preference: str = ""
    push_trigger_option: str = ""
    has_ai_bot: bool = False
    has_bot: bool = False
    is_ai_agent_channel: bool = False
    ignore_profanity_filter: bool = False
    unread_count: int = 0
    last_message_id: int | None = None
    last_message_at: datetime | None = None
    first_synced_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_synced_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    raw_json: str = ""
