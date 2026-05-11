"""Hinge match domain model."""

from dataclasses import dataclass
from datetime import datetime

from hinge.domain.models.profile import HingeProfile


@dataclass
class HingeMatch:
    """A match from /connection/v2 or Sendbird."""

    subject_id: str
    matched_at: datetime | None = None
    profile: HingeProfile | None = None
    sendbird_channel_url: str | None = None
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
