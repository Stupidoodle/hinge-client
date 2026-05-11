"""Hinge swipe session domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class HingeSwipeSession:
    """Analytics record for a Hinge swiping session."""

    id: int | None = None
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    ended_at: datetime | None = None
    profiles_seen: int = 0
    likes_sent: int = 0
    skips_sent: int = 0
    notes_sent: int = 0
    matches: int = 0
    min_score_threshold: float = 0.0
