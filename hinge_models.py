"""Pydantic schemas for API responses.

The holy texts. Parsing this much JSON without Pydantic is a war crime.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import IntEnum
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel
from typing import Any, Literal, TYPE_CHECKING
from uuid import uuid4

from hinge_enums import (
    ChildrenStatusEnum,
    ContentType,
    DatingIntentionEnum,
    DrinkingStatusEnum,
    DrugStatusEnum,
    EducationAttainedEnum,
    EthnicitiesEnum,
    GenderPreferences,
    LanguageEnum,
    MarijuanaStatusEnum,
    PoliticsEnum,
    QuestionId,
    RelationshipTypeEnum,
    ReligionEnum,
    SmokingStatusEnum,
)
from logging_config import logger as log

if TYPE_CHECKING:
    from hinge_client import HingeClient  # noqa: F401


class BaseHingeModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="ignore",
        populate_by_name=True,
    )


class ActiveHingeModel(BaseHingeModel):
    """Base model that can hold a client instance to perform actions."""

    client: Any = Field(exclude=True)


class ContentHingeModel(ActiveHingeModel):
    """Base model for content-related actions that can a subject instance."""

    subject: RecommendationSubject


class ChildrenStatus(BaseHingeModel):
    """Wrapper for children status list for the /user/v3 endpoint."""

    value: ChildrenStatusEnum | None = None
    visible: bool


class DatingIntention(BaseHingeModel):
    """Wrapper for dating intentions list for the /user/v3 endpoint."""

    value: DatingIntentionEnum | None = None
    visible: bool


class DrinkingStatus(BaseHingeModel):
    """Wrapper for drinking status list for the /user/v3 endpoint."""

    value: DrinkingStatusEnum | None = None
    visible: bool


class DrugStatus(BaseHingeModel):
    """Wrapper for drug status list for the /user/v3 endpoint."""

    value: DrugStatusEnum | None = None
    visible: bool


class MarijuanaStatus(BaseHingeModel):
    """Wrapper for marijuana status list for the /user/v3 endpoint."""

    value: MarijuanaStatusEnum | None = None
    visible: bool


class SmokingStatus(BaseHingeModel):
    """Wrapper for smoking status list for the /user/v3 endpoint."""

    value: SmokingStatusEnum | None = None
    visible: bool


class Religion(BaseHingeModel):
    """Wrapper for religions list for the /user/v3 endpoint."""

    value: list[ReligionEnum] | None = None
    visible: bool


class Politics(BaseHingeModel):
    """Wrapper for politics list for the /user/v3 endpoint."""

    value: PoliticsEnum | None = None
    visible: bool


class RelationshipType(BaseHingeModel):
    """Wrapper for relationship types list for the /user/v3 endpoint."""

    value: list[RelationshipTypeEnum] | None = None
    visible: bool


class Language(BaseHingeModel):
    """Wrapper for languages list for the /user/v3 endpoint."""

    value: list[LanguageEnum] | None = None
    visible: bool


class Ethnicities(BaseHingeModel):
    """Wrapper for ethnicities list for the /user/v3 endpoint."""

    value: list[EthnicitiesEnum] | None = None
    visible: bool


class Educations(BaseHingeModel):
    """Wrapper for education list for the /user/v3 endpoint."""

    value: list[str] | None = None
    visible: bool


class FamilyPlans(BaseHingeModel):
    """Wrapper for family plans list for the /user/v3 endpoint."""

    value: int | None = None  # TODO: Define proper enum
    visible: bool


class GenderIdentity(BaseHingeModel):
    """Wrapper for gender identity for the /user/v3 endpoint."""

    value: int | None = None  # 26 is Man I guess? TODO: Define proper enum
    visible: bool


class HomeTown(BaseHingeModel):
    """Wrapper for hometown information for the /user/v3 endpoint."""

    value: str | None = None
    visible: bool


class JobTitle(BaseHingeModel):
    """Wrapper for job title information for the /user/v3 endpoint."""

    value: str | None = None
    visible: bool


class Pets(BaseHingeModel):
    """Wrapper for pets information for the /user/v3 endpoint."""

    value: list[int] | None = None  # TODO: Define proper enum
    visible: bool


class SexualOrientation(BaseHingeModel):
    """Wrapper for sexual orientation information for the /user/v3 endpoint."""

    value: list[int] | None = None  # TODO: Define proper enum
    visible: bool


class RangeDetails(BaseHingeModel):
    """Wrapper for range details for the /user/v3 endpoint."""

    max: int | None = None
    min: int | None = None


class GenderedRange(BaseHingeModel):
    """Schema for gender-specific range, e.g. age or height."""

    men: RangeDetails | None = Field(default=None, alias="0")
    women: RangeDetails | None = Field(default=None, alias="1")
    non_binary_people: RangeDetails | None = Field(default=None, alias="3")


class GenderedDealbreaker(BaseHingeModel):
    """Schema for gender-specific dealbreakers."""

    men: bool | None = Field(default=None, alias="0")
    women: bool | None = Field(default=None, alias="1")
    non_binary_people: bool | None = Field(default=None, alias="3")


class Dealbreakers(BaseHingeModel):
    """Schema for dealbreaker flags in user preferences."""

    marijuana: bool
    smoking: bool
    max_distance: bool
    drinking: bool
    education_attained: bool
    gendered_height: GenderedDealbreaker = Field(..., alias="genderedHeight")
    politics: bool
    relationship_types: bool
    drugs: bool
    dating_intentions: bool
    family_plans: bool
    gendered_age: GenderedDealbreaker = Field(..., alias="genderedAge")
    religions: bool
    ethnicities: bool
    children: bool


class Preferences(BaseHingeModel):
    """Schema to update user preferences (PATCH /preferences/v2/selected)."""

    gendered_age_ranges: GenderedRange = Field(..., alias="genderedAgeRanges")
    dealbreakers: Dealbreakers
    religions: list[ReligionEnum]
    drinking: list[DrinkingStatusEnum]
    gendered_height_ranges: GenderedRange = Field(..., alias="genderedHeightRanges")
    marijuana: list[MarijuanaStatusEnum]
    relationship_types: list[RelationshipTypeEnum]
    drugs: list[DrugStatusEnum]
    max_distance: int
    children: list[ChildrenStatusEnum]
    ethnicities: list[EthnicitiesEnum]
    smoking: list[SmokingStatusEnum]
    education_attained: list[EducationAttainedEnum]
    family_plans: list[int]  # TODO: Define proper enum
    dating_intentions: list[DatingIntentionEnum]
    politics: list[PoliticsEnum]
    gender_preferences: list[GenderPreferences] = Field(..., alias="genderPreferences")

    @model_validator(mode="after")
    def validate_dealbreakers(self) -> "Preferences":
        """Validate that dealbreakers are not set for 'OPEN_TO_ALL' options."""
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, list) and all(
                isinstance(v, IntEnum) for v in field_value
            ):
                if 0 in field_value:
                    raise ValueError(
                        f"Dealbreaker field '{field_name}' cannot be "
                        f"'PREFER_NOT_TO_SAY' in Preferences."
                    )

                if -1 in field_value:
                    if len(field_value) > 1:
                        raise ValueError(
                            f"Dealbreaker field '{field_name}' cannot be "
                            f"'OPEN_TO_ALL' and have other values at the same time."
                        )

                    if getattr(self.dealbreakers, field_name):
                        raise ValueError(
                            f"Dealbreaker field '{field_name}' cannot be "
                            f"'OPEN_TO_ALL' and set to True in dealbreakers."
                        )

        return self


class Works(BaseHingeModel):
    """Wrapper for works information for the /user/v3 endpoint."""

    value: str | None = None
    visible: bool


class HingeAuthToken(BaseHingeModel):
    """Schema for the main Hinge Bearer token."""

    identity_id: str
    token: str
    expires: datetime


class SendbirdAuthToken(BaseHingeModel):
    """Schema for the Sendbird Bearer token."""

    token: str
    expires: datetime


class LikeLimit(BaseHingeModel):
    """Schema for the daily like limit status."""

    likes_left: int
    super_likes_left: int = Field(  # If you have those, consider yourself lost
        alias="superlikesLeft"
    )
    free_super_likes_left: int | None = None  # Added for free super likes
    free_super_like_expiration: datetime | None = None


class LikeResponse(BaseHingeModel):
    """Schema for the response after liking a user."""

    limit: LikeLimit


class TextReview(BaseHingeModel):
    """Schema for the text moderation pre-flight check."""

    is_harmful: bool


class RecommendationSubject(ActiveHingeModel):
    """A single user recommendation from the feed."""

    subject_id: str
    rating_token: str
    origin: str | None = None

    async def skip(self) -> dict[str, Any]:
        """Skip this recommendation.

        Returns:
            dict[str, Any]: The response from the server.

        Raises:
            httpx.HTTPStatusError: If the request fails.

        """
        log.info("Skipping user", subject_id=self.subject_id)
        payload = CreateRate(
            rating="skip",
            subject_id=self.subject_id,
            rating_token=self.rating_token,
            session_id=self.client.session_id,
            initiated_with=None,
            origin=self.origin,
        )

        response = await self.client.client.post(
            "/rate/v2/initiate",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self.client._get_default_headers(),  # noqa
        )
        response.raise_for_status()
        self.client.remove_recommendation(self.subject_id)
        return response.json()

    async def get_full_content(self) -> ProfileContent:
        """Fetch the full content for this subject and inject dependencies.

        Returns:
            ProfileContent: The full content of the user, including photos and answers.

        """
        log.info("Hydrating full content for user", subject_id=self.subject_id)
        return await self.client.get_profile_content(self.subject_id)


class RecommendationsFeed(BaseHingeModel):
    """A feed of user recommendations."""

    origin: str
    subjects: list[RecommendationSubject]


class RecommendationsResponse(BaseHingeModel):
    """The full response from the recommendations' endpoint."""

    feeds: list[RecommendationsFeed]


class Location(BaseHingeModel):
    """Schema for a user's location."""

    name: str
    latitude: float | None = None
    longitude: float | None = None
    metro_area: str | None = None
    metro_area_v2: str | None = None
    country_short: str | None = None
    admin_area1_long: str | None = None
    admin_area1_short: str | None = None
    admin_area2: str | None = None


class Profile(BaseHingeModel):
    """Schema for a user's profile data (can be public or self-profile subset)."""

    age: int | None = None  # Added from /user/v3
    birthday: datetime | None = None  # Added from /user/v3
    covid_vax: int | None = None
    children: ChildrenStatus | ChildrenStatusEnum | None = Field(
        union_mode="left_to_right"
    )  # Using new Enum
    dating_intention: DatingIntention | DatingIntentionEnum | None = Field(
        union_mode="left_to_right"
    )  # Using new Enum
    dating_intention_text: str | None = None
    drinking: DrinkingStatus | DrinkingStatusEnum | None = Field(
        union_mode="left_to_right"
    )  # Using new Enum
    drugs: DrugStatus | DrugStatusEnum | None = Field(
        union_mode="left_to_right"
    )  # Using new Enum
    education_attained: EducationAttainedEnum | None = None  # Added from /user/v3
    educations: Educations | list[str] | None = None
    ethnicities: Ethnicities | list[EthnicitiesEnum] | None = None
    ethnicities_text: str | None = None  # Added from /user/v3
    family_plans: FamilyPlans | int | None = None
    first_name: str
    first_completed_date: datetime | None = None  # Added from /user/v3
    gender_id: int | None = None  # Added from /user/v3
    gender_identity_id: GenderIdentity | int | None = None
    gender_identity: str | None = None  # Added from /user/v3
    height: int | None = None
    hometown: HomeTown | str | None = None
    job_title: JobTitle | str | None = None
    languages_spoken: list[Language] | list[LanguageEnum] | None = (
        None  # Using new Enum
    )
    last_name: str | None = None
    location: Location
    match_note: str | None = None  # Added from /user/v3
    marijuana: MarijuanaStatus | MarijuanaStatusEnum | None = Field(
        union_mode="left_to_right"
    )  # Using new Enum
    pets: Pets | list[int] | None = None
    politics: Politics | PoliticsEnum | None = Field(union_mode="left_to_right")
    pronouns: list[int] | None = None
    relationship_type_ids: RelationshipType | list[RelationshipTypeEnum] | None = (
        None  # Using new Enum
    )
    relationship_types_text: str | None = None
    religions: Religion | ReligionEnum | None = Field(
        union_mode="left_to_right"
    )  # Using new Enum
    selfie_verified: bool | None = None
    sexual_orientations: SexualOrientation | list[int] | None = None
    smoking: SmokingStatus | SmokingStatusEnum | None = Field(
        union_mode="left_to_right"
    )
    works: Works | str | None = None
    zodiac: int | None = None  # Added from /user/v3
    last_active_status_id: int | None = None
    did_just_join: bool | None = Field(default=None, alias="didjustJoin")


class UserProfile(BaseHingeModel):
    """Schema for a user's public profile data."""

    user_id: str
    profile: Profile


class SelfProfileResponse(BaseHingeModel):
    """Schema for the authenticated user's full profile data (GET /user/v3)."""

    user_id: str
    created: datetime
    registered: datetime
    modified: datetime
    last_active_opt_in: bool
    profile: Profile
    paused: bool


class BoundingBox(BaseHingeModel):
    """Schema for bounding box coordinates within a photo."""

    top_left: dict[str, float]
    bottom_right: dict[str, float]


class CreateRateContentPrompt(BaseHingeModel):
    """Payload for the prompt object inside the rate content."""

    answer: str
    content_id: str
    question: str


class CreateRateContent(BaseHingeModel):
    """Dynamic content payload for the main rating request."""

    comment: str | None = None
    photo: PhotoContent | None = None
    prompt: CreateRateContentPrompt | None = None

    @model_validator(mode="after")
    def check_photo_or_prompt(self) -> "CreateRateContent":
        """Ensure that either photo or prompt is provided, but not both."""
        if self.photo is None and self.prompt is None:
            raise ValueError(
                "Either 'photo' or 'prompt' must be set in RateContentPayload"
            )

        if self.photo is not None and self.prompt is not None:
            raise ValueError(
                "'photo' and 'prompt' cannot both be set in RateContentPayload"
            )

        return self


class CreateRate(BaseHingeModel):
    """Schema for the /rate/v2/initiate endpoint."""

    rating_id: str = Field(default_factory=lambda: str(uuid4()).upper())
    hcm_run_id: str | None = None
    session_id: str
    content: CreateRateContent | None = None
    created: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    rating_token: str
    initiated_with: Literal["standard", "superlike"] | None = None
    rating: Literal["like", "note", "skip"]
    has_pairing: bool = False  # No clue what this is
    origin: str | None = "compatibles"  # Could also be standouts maybe?
    subject_id: str


class PhotoContent(ContentHingeModel):
    """Schema for a single photo in a user's profile."""

    bounding_box: BoundingBox | None = None  # Added
    caption: str | None = None
    cdn_id: str
    content_id: str
    location: str | None = None
    prompt_id: str | None = None
    source: str | None = None
    source_id: str | None = None  # Added
    video_url: str | None = None  # Added
    p_hash: str | None = None  # Added
    url: str
    width: int | None = None  # Added
    height: int | None = None  # Added
    selfie_verified: bool | None = None

    async def like(
        self, comment: str | None = None, use_superlike: bool = False
    ) -> LikeResponse:
        """Like this specific photo, with an optional comment.

        Args:
            comment (str): Optional comment to add with the like.
            use_superlike (bool): Whether to use a superlike instead of a regular like.

        Returns:
            LikeResponse: The response containing the updated like limits.

        """
        log.info(
            "Initiating like on photo",
            subject_id=self.subject.subject_id,
            content_id=self.content_id,
            has_comment=comment is not None,
            use_superlike=use_superlike,
        )

        try:
            result = await self.client.rate_user(
                subject=self.subject,
                content_item=self,
                comment=comment,
                use_superlike=use_superlike,
            )
        except Exception as e:
            log.error(
                "Failed to like photo",
                subject_id=self.subject.subject_id,
                content_id=self.content_id,
                error=str(e),
            )
            raise e

        self.client.remove_recommendation(self.subject.subject_id)
        return result


class Feedback(BaseHingeModel):
    """Schema for the feedback on a prompt."""

    evaluation: str | None = None
    detail: str | None = None
    feedback_token: str | None = None


class TranscriptionMetadata(BaseHingeModel):
    """Placeholder for transcription metadata."""

    content_id: str | None = None
    position: int | None = None
    question_id: QuestionId | None = None
    type: Literal["voice", "video", "text"] | None = None
    url: str | None = None
    cdn_id: str | None = None
    waveform: str | None = None
    transcription: str | None = None
    languageCode: str | None = None  # e.g. 'en-US'
    status: str | None = None  # e.g. 'success'


class TextAnswer(BaseHingeModel):
    """Schema for the text content of a prompt answer."""

    response: str
    question_id: str  # The questionId is duplicated here for some reason


class AnswerContentPayload(BaseHingeModel):
    """Schema for a single answer object in the PUT /content/v1/answers payload."""

    position: int
    question_id: QuestionId
    text_answer: TextAnswer


class AnswerContent(ContentHingeModel, TranscriptionMetadata):
    """Schema for a prompt answer."""

    content_id: str
    position: int | None = None  # Added
    question_id: QuestionId
    response: str | None = None  # NOTE: This can be None for voice/video answers
    transcription_metadata: TranscriptionMetadata | None = None  # Added
    feedback: Feedback | None = None  # Added

    async def like(
        self, comment: str | None = None, use_superlike: bool = False
    ) -> LikeResponse:
        """Like this specific answer, with an optional comment.

        Args:
            comment (str): Optional comment to add with the like.
            use_superlike (bool): Whether to use a superlike instead of a regular like.

        Returns:
            LikeResponse: The response containing the updated like limits.

        """
        log.info(
            "Initiating like on answer",
            subject_id=self.subject.subject_id,
            content_id=self.content_id,
            has_comment=comment is not None,
            use_superlike=use_superlike,
        )

        self.client.remove_recommendation(self.subject.subject_id)

        return await self.client.rate_user(
            subject=self.subject,
            content_item=self,
            comment=comment,
            use_superlike=use_superlike,
        )

    @field_validator("transcription_metadata", mode="before")
    def empty_dict_to_none(cls, v):
        """Convert empty dict to None for transcription metadata."""
        if isinstance(v, dict) and not v:
            return None
        return v


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

    name: str  # e.g. "Self-care", "Story time", etc.
    slug: str  # e.g. "self-care", "storytime", etc.
    is_visible: bool
    is_new: bool


class PromptContent(BaseHingeModel):
    """Schema for a user's prompt content."""

    content_id: str
    question_id: QuestionId
    options: list[str]
    selected_option_index: int | None = None


class PromptsResponse(BaseHingeModel):
    """Schema for the full prompts API response."""

    prompts: list[Prompt]
    categories: list[PromptCategory]


class ProfileContentContent(BaseHingeModel):
    """Wrapper for the content field in ProfileContent."""

    photos: list[PhotoContent]
    answers: list[AnswerContent]
    prompt_poll: PromptContent | None = None


class ProfileContent(BaseHingeModel):
    """Schema for a user's full content (photos, answers, etc.)."""

    user_id: str
    content: ProfileContentContent


class SelfContentResponse(BaseHingeModel):
    """Schema for the authenticated user's content data (GET /content/v2)."""

    content: ProfileContentContent
