"""Recommendation feed schemas for the Hinge recommendations endpoint."""

from hinge.models.base import BaseHingeModel


class TextReview(BaseHingeModel):
    """Schema for the text moderation pre-flight check."""

    is_harmful: bool


class SecondChance(BaseHingeModel):
    """Second chance metadata on recycled recommendations."""

    second_chance_source: int = 0


class Enhancements(BaseHingeModel):
    """Enhancement flags on a recommendation subject."""

    second_chance: SecondChance | None = None


class RecommendationSubject(BaseHingeModel):
    """A single user recommendation from the feed (pure data, no client)."""

    subject_id: str
    rating_token: str
    origin: str | None = None
    enhancements: Enhancements | None = None


class RecommendationsFeed(BaseHingeModel):
    """A feed of user recommendations."""

    origin: str
    subjects: list[RecommendationSubject]


class RecommendationsResponse(BaseHingeModel):
    """The full response from the recommendations endpoint."""

    feeds: list[RecommendationsFeed]
