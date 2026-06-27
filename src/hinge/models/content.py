"""Profile content schemas: photos, prompt answers, and related media."""

from typing import Literal

from pydantic import field_validator

from hinge.models.attributes import BoundingBox
from hinge.models.base import BaseHingeModel
from hinge.models.prompts import DateIdeaContent, PromptContent, VideoPromptContent


class PromptEvaluation(BaseHingeModel):
    """Response from POST /content/v1/answer/evaluate."""

    evaluation: str | None = None
    detail: str | None = None
    feedback_token: str | None = None


class ContentSettings(BaseHingeModel):
    """Response/request for GET/PATCH /content/v1/settings."""

    is_smart_photo_opt_in: bool = False
    is_convo_starters_opt_in: bool = False


class VideoDetail(BaseHingeModel):
    """Schema for an embedded video variant in a photo (sd/hd quality)."""

    height: int | None = None
    width: int | None = None
    url: str
    quality: str | None = None  # "sd" | "hd"


class PhotoContent(BaseHingeModel):
    """Schema for a single photo in a user's profile (pure data)."""

    bounding_box: BoundingBox | None = None
    caption: str | None = None
    cdn_id: str
    content_id: str
    location: str | None = None
    prompt_id: str | None = None
    source: str | None = None
    source_id: str | None = None
    video_url: str | None = None
    videos: list[VideoDetail] = []
    p_hash: str | None = None
    url: str
    width: int | None = None
    height: int | None = None
    selfie_verified: bool | None = None


class Feedback(BaseHingeModel):
    """Schema for the feedback on a prompt."""

    evaluation: str | None = None
    detail: str | None = None
    feedback_token: str | None = None


class TranscriptionMetadata(BaseHingeModel):
    """Placeholder for transcription metadata."""

    content_id: str | None = None
    position: int | None = None
    question_id: str | None = None
    type: Literal["voice", "video", "text"] | None = None
    url: str | None = None
    cdn_id: str | None = None
    waveform: str | None = None
    transcription: str | None = None
    languageCode: str | None = None  # noqa: N815
    status: str | None = None


class TextAnswer(BaseHingeModel):
    """Schema for the text content of a prompt answer."""

    response: str
    question_id: str


class AnswerContentPayload(BaseHingeModel):
    """Schema for a single answer in the PUT /content/v1/answers payload."""

    position: int
    question_id: str
    text_answer: TextAnswer


class AnswerContent(TranscriptionMetadata):
    """Schema for a prompt answer (pure data)."""

    content_id: str
    position: int | None = None
    question_id: str
    response: str | None = None
    transcription_metadata: TranscriptionMetadata | None = None
    feedback: Feedback | None = None

    @field_validator("transcription_metadata", mode="before")
    @classmethod
    def empty_dict_to_none(cls, v):
        """Convert empty dict to None for transcription metadata."""
        if isinstance(v, dict) and not v:
            return None
        return v

    @field_validator("transcription", mode="before")
    @classmethod
    def coerce_transcription(cls, v):
        """Handle transcription as string or object with transcript field."""
        if isinstance(v, dict):
            return v.get("transcript") or v.get("transcription") or ""
        return v


class ProfileContentContent(BaseHingeModel):
    """Wrapper for the content field in ProfileContent."""

    photos: list[PhotoContent]
    answers: list[AnswerContent]
    prompt_poll: PromptContent | None = None
    video_prompt: VideoPromptContent | None = None
    date_idea: DateIdeaContent | None = None


class ProfileContent(BaseHingeModel):
    """Schema for a user's full content (photos, answers, etc.)."""

    user_id: str
    content: ProfileContentContent


class SelfContentResponse(BaseHingeModel):
    """Schema for the authenticated user's content data (GET /content/v2)."""

    content: ProfileContentContent
