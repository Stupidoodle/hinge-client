"""Hinge chat message domain model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class HingeChatMessage:
    """A message within a Sendbird chat channel."""

    message_id: int
    channel_url: str
    sender_sendbird_id: str
    is_from_me: bool
    message_type: str
    body: str
    data: str
    custom_type: str
    created_at: datetime
    message_survival_seconds: int
    message_retention_hour: int
    raw_json: str
    updated_at: datetime | None = None
    dedup_id: str | None = None
    attempt_id: str | None = None
    is_match_message: bool = False
    origin: str | None = None
    sent_from_app_version: str | None = None
    sent_from_platform: str | None = None
    file_url: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    file_name: str | None = None
    is_removed: bool = False
    is_silent: bool = False
    is_op_msg: bool = False
