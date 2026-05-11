"""Hinge recommendation domain model."""

from dataclasses import dataclass

from hinge.domain.models.profile import HingeProfile


@dataclass
class Recommendation:
    """A recommendation from the feed, with rating token for voting."""

    subject_id: str
    rating_token: str
    origin: str
    profile: HingeProfile | None = None
    is_second_chance: bool = False
    second_chance_source: int | None = None
