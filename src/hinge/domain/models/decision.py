"""Hinge decision domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class HingeDecision:
    """Record of a like/skip/note decision."""

    id: int | None = None
    profile_subject_id: str = ""
    action: str = "skip"  # like, skip, note, superlike
    content_id: str | None = None
    comment: str | None = None
    score: float | None = None
    reasoning: str | None = None
    decided_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    session_id: int | None = None
    is_match: bool = False
