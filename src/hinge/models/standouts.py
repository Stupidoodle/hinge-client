"""Standouts feed schemas for the /standouts/v2 and /standouts/v3 endpoints."""

from datetime import datetime

from hinge.models.attributes import BoundingBox
from hinge.models.base import BaseHingeModel


class StandoutPhoto(BaseHingeModel):
    """Photo content in a standout."""

    url: str | None = None
    bounding_box: BoundingBox | None = None
    content_id: str
    prompt_id: str | None = None


class StandoutContent(BaseHingeModel):
    """Content preview for a standout."""

    photo: StandoutPhoto | None = None


class StandoutSubject(BaseHingeModel):
    """A standout profile from /standouts/v2."""

    subject_id: str
    rating_token: str
    content: StandoutContent | None = None


class StandoutsV2Response(BaseHingeModel):
    """Response from /standouts/v2 with free/paid split."""

    status: str | None = None
    expiration: datetime | None = None
    free: list[StandoutSubject] = []
    paid: list[StandoutSubject] = []


class StandoutsV3Response(BaseHingeModel):
    """Response from /standouts/v3 (flat list, supports ETag caching)."""

    status: str | None = None
    standouts: list[StandoutSubject] = []
    expiration: datetime | None = None
    view_token: str | None = None
