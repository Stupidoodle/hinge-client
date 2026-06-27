"""Rating, like, and likes-you schemas for the Hinge /rate and /like APIs."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from hinge.models.base import BaseHingeModel


class LikeLimit(BaseHingeModel):
    """Schema for the daily like limit status."""

    likes_left: int
    super_likes_left: int = Field(alias="superlikesLeft")
    free_super_likes_left: int | None = None
    free_super_like_expiration: datetime | None = None


class LikeResponse(BaseHingeModel):
    """Schema for the response after liking a user."""

    limit: LikeLimit


class RatePhoto(BaseHingeModel):
    """Minimal photo payload for the /rate/v2/initiate endpoint."""

    content_id: str
    url: str
    cdn_id: str


class CreateRateContentPrompt(BaseHingeModel):
    """Payload for the prompt object inside the rate content."""

    answer: str
    content_id: str
    question: str


class CreateRateContent(BaseHingeModel):
    """Dynamic content payload for the main rating request."""

    comment: str | None = None
    photo: RatePhoto | None = None
    prompt: CreateRateContentPrompt | None = None

    @model_validator(mode="after")
    def check_photo_or_prompt(self) -> CreateRateContent:
        """Ensure that either photo or prompt is provided, but not both."""
        if self.photo is None and self.prompt is None:
            raise ValueError(
                "Either 'photo' or 'prompt' must be set in RateContentPayload",
            )
        if self.photo is not None and self.prompt is not None:
            raise ValueError(
                "'photo' and 'prompt' cannot both be set in RateContentPayload",
            )
        return self


class CreateRate(BaseHingeModel):
    """Schema for the /rate/v2/initiate endpoint (13 fields)."""

    rating_id: str = Field(default_factory=lambda: str(uuid4()).upper())
    hcm_run_id: str | None = None
    session_id: str
    content: CreateRateContent | None = None
    created: str = Field(
        default_factory=lambda: (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
    )
    rating_token: str
    initiated_with: Literal["standard", "superlike"] | None = None
    rating: Literal["like", "note", "skip"]
    has_pairing: bool = False
    origin: str | None = "discover"
    subject_id: str
    top_photo_content_id: str | None = None
    data: dict[str, Any] | None = None


class RespondRate(BaseHingeModel):
    """Schema for POST /rate/v2/respond (responding to incoming likes)."""

    rating_id: str = Field(default_factory=lambda: str(uuid4()).upper())
    subject_id: str
    session_id: str
    rating: Literal["like", "block"]
    origin: str | None = None
    has_pairing: bool = False
    content: CreateRateContent | None = None
    created: str = Field(
        default_factory=lambda: (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
    )
    data: dict[str, Any] | None = None
    initiated_with: Literal["standard", "superlike"] | None = None
    sort_type: str | None = None


class MatchRate(BaseHingeModel):
    """Schema for POST /rate/v2/match (block from match/chat screen)."""

    rating_id: str = Field(default_factory=lambda: str(uuid4()).upper())
    subject_id: str
    session_id: str
    rating: Literal["block"] = "block"
    origin: str | None = None
    second_chance_eligible: bool | None = None


class LikeSortCategory(BaseHingeModel):
    """Sort option for Likes You."""

    id: str
    title: str


class LikeImpression(BaseHingeModel):
    """An incoming like (Impression) from GET /like/v2."""

    subject_id: str
    created: str | None = None
    rating: str | None = None
    pairing: str | None = None
    show_match_note: bool = False
    expires: str | None = None
    source: str | None = None
    initiated_with: str | None = None
    hidden: bool = False
    rating_token: str | None = None


class SortedLikes(BaseHingeModel):
    """Sorted likes group from GET /like/v2."""

    sort_id: str = Field(alias="sortID")
    data: list[LikeImpression] = []


class HiddenLike(BaseHingeModel):
    """A moderation-hidden like."""

    id: str
    reason: str | None = None


class LikesYouResponse(BaseHingeModel):
    """Response from GET /like/v2."""

    likes: list[LikeImpression] = []
    sorts: list[LikeSortCategory] = []
    sorted_likes: list[SortedLikes] = []
    hidden_likes: list[HiddenLike] = []
    view_token: str | None = None
