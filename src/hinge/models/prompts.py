"""Prompt library and prompt-content schemas for the Hinge API."""

from hinge.enums import ContentType
from hinge.models.attributes import BoundingBox
from hinge.models.base import BaseHingeModel


class Prompt(BaseHingeModel):
    """Schema for an individual prompt."""

    id: str
    prompt: str
    is_selectable: bool
    placeholder: str = ""
    is_new: bool
    categories: list[str] = []
    content_types: list[ContentType] = []


class PromptCategory(BaseHingeModel):
    """Schema for prompt category metadata."""

    name: str
    slug: str
    is_visible: bool
    is_new: bool


class PromptContent(BaseHingeModel):
    """Schema for a user's prompt poll content."""

    content_id: str
    question_id: str
    options: list[str]
    selected_option_index: int | None = None


class VideoPromptContent(BaseHingeModel):
    """Schema for a standalone video prompt response on a profile."""

    cdn_id: str | None = None
    content_id: str
    video_url: str | None = None
    question_id: str | None = None
    thumbnail_url: str | None = None
    bounding_box: BoundingBox | None = None


class DateIdeaContent(BaseHingeModel):
    """Schema for a date idea prompt response on a profile."""

    content_id: str
    question_id: str | None = None
    options: list[str] = []


class PromptsResponse(BaseHingeModel):
    """Schema for the full prompts API response."""

    prompts: list[Prompt]
    categories: list[PromptCategory]
