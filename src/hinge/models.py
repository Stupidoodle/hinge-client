"""Pydantic schemas for Hinge API responses.

Pure data models — no client references, no Active Record pattern.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from hinge.enums import (
    ContentType,
    GenderPreferences,
    QuestionId,
)


class BaseHingeModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="ignore",
        populate_by_name=True,
    )


class ChildrenStatus(BaseHingeModel):
    """Wrapper for children status list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class DatingIntention(BaseHingeModel):
    """Wrapper for dating intentions list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class DrinkingStatus(BaseHingeModel):
    """Wrapper for drinking status list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class DrugStatus(BaseHingeModel):
    """Wrapper for drug status list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class MarijuanaStatus(BaseHingeModel):
    """Wrapper for marijuana status list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class SmokingStatus(BaseHingeModel):
    """Wrapper for smoking status list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class Religion(BaseHingeModel):
    """Wrapper for religions list for the /user/v3 endpoint."""

    value: list[int] | None = None
    visible: bool


class Politics(BaseHingeModel):
    """Wrapper for politics list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class RelationshipType(BaseHingeModel):
    """Wrapper for relationship types list for the /user/v3 endpoint."""

    value: list[int] | None = None
    visible: bool


class Language(BaseHingeModel):
    """Wrapper for languages list for the /user/v3 endpoint."""

    value: list[int] | None = None
    visible: bool


class Ethnicities(BaseHingeModel):
    """Wrapper for ethnicities list for the /user/v3 endpoint."""

    value: list[int] | None = None
    visible: bool


class Educations(BaseHingeModel):
    """Wrapper for education list for the /user/v3 endpoint."""

    value: list[str] | None = None
    visible: bool


class FamilyPlans(BaseHingeModel):
    """Wrapper for family plans list for the /user/v3 endpoint."""

    value: int | None = None
    visible: bool


class GenderIdentity(BaseHingeModel):
    """Wrapper for gender identity for the /user/v3 endpoint."""

    value: int | None = None
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

    value: list[int] | None = None
    visible: bool


class SexualOrientation(BaseHingeModel):
    """Wrapper for sexual orientation information for the /user/v3 endpoint."""

    value: list[int] | None = None
    visible: bool


class Works(BaseHingeModel):
    """Wrapper for works information for the /user/v3 endpoint."""

    value: str | None = None
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
    religions: list[int]
    drinking: list[int]
    gendered_height_ranges: GenderedRange = Field(..., alias="genderedHeightRanges")
    marijuana: list[int]
    relationship_types: list[int]
    drugs: list[int]
    max_distance: int
    children: list[int]
    ethnicities: list[int]
    smoking: list[int]
    education_attained: list[int]
    family_plans: list[int]
    dating_intentions: list[int]
    politics: list[int]
    gender_preferences: list[GenderPreferences] = Field(
        ...,
        alias="genderPreferences",
    )

    @model_validator(mode="after")
    def validate_dealbreakers(self) -> Preferences:
        """Validate that dealbreakers are not set for 'OPEN_TO_ALL' options."""
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, list) and all(
                isinstance(v, int) for v in field_value
            ):
                if 0 in field_value:
                    raise ValueError(
                        f"Dealbreaker field '{field_name}' cannot be "
                        f"'PREFER_NOT_TO_SAY' in Preferences.",
                    )
                if -1 in field_value:
                    if len(field_value) > 1:
                        raise ValueError(
                            f"Dealbreaker field '{field_name}' cannot be "
                            f"'OPEN_TO_ALL' and have other values.",
                        )
                    if getattr(self.dealbreakers, field_name):
                        raise ValueError(
                            f"Dealbreaker field '{field_name}' cannot be "
                            f"'OPEN_TO_ALL' and set to True in dealbreakers.",
                        )
        return self


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
    super_likes_left: int = Field(alias="superlikesLeft")
    free_super_likes_left: int | None = None
    free_super_like_expiration: datetime | None = None


class LikeResponse(BaseHingeModel):
    """Schema for the response after liking a user."""

    limit: LikeLimit


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

    age: int | None = None
    birthday: datetime | None = None
    covid_vax: int | None = None
    children: ChildrenStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    dating_intention: DatingIntention | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    dating_intention_text: str | None = None
    drinking: DrinkingStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    drugs: DrugStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    education_attained: int | None = None
    educations: Educations | list[str] | None = None
    ethnicities: Ethnicities | list[int] | None = None
    ethnicities_text: str | None = None
    family_plans: FamilyPlans | int | None = None
    first_name: str
    first_completed_date: datetime | None = None
    gender_id: int | None = None
    gender_identity_id: GenderIdentity | int | None = None
    gender_identity: str | None = None
    height: int | None = None
    hometown: HomeTown | str | None = None
    job_title: JobTitle | str | None = None
    languages_spoken: Language | list[Language] | list[int] | None = None
    last_name: str | None = None
    location: Location
    match_note: str | None = None
    marijuana: MarijuanaStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    pets: Pets | list[int] | None = None
    politics: Politics | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    pronouns: list[int] | None = None
    relationship_type_ids: RelationshipType | list[int] | None = None
    relationship_types_text: str | None = None
    religions: Religion | list[int] | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    selfie_verified: bool | None = None
    sexual_orientations: SexualOrientation | list[int] | None = None
    smoking: SmokingStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    works: Works | str | None = None
    zodiac: int | None = None
    last_active_status_id: int | None = None
    did_just_join: bool | None = Field(default=None, alias="didjustJoin")


class UserProfile(BaseHingeModel):
    """Schema for a user's public profile data (v3 — demographics only)."""

    user_id: str
    profile: Profile


class ProfileV2(BaseHingeModel):
    """V2 profile — includes photos and answers inline (unlike v3)."""

    age: int | None = None
    first_name: str
    gender_id: int | None = None
    height: int | None = None
    location: Location
    selfie_verified: bool | None = None
    did_just_join: bool | None = Field(default=None, alias="didjustJoin")
    last_active_status_id: int | None = None
    hometown: HomeTown | str | None = None
    job_title: JobTitle | str | None = None
    works: Works | list[str] | str | None = None
    education_attained: int | None = None
    educations: Educations | list[str] | None = None
    children: ChildrenStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    dating_intention: DatingIntention | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    drinking: DrinkingStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    drugs: DrugStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    marijuana: MarijuanaStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    smoking: SmokingStatus | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    ethnicities: Ethnicities | list[int] | None = None
    ethnicities_text: str | None = None
    family_plans: FamilyPlans | int | None = None
    languages_spoken: Language | list[Language] | list[int] | None = None
    last_name: str | None = None
    pets: Pets | list[int] | None = None
    politics: Politics | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    pronouns: list[int] | None = None
    relationship_types: RelationshipType | list[int] | None = None
    relationship_types_text: str | None = None
    religions: Religion | list[int] | int | None = Field(
        default=None,
        union_mode="left_to_right",
    )
    sexual_orientations: SexualOrientation | list[int] | None = None
    zodiac: int | None = None
    dating_intention_text: str | None = None
    last_active_status: str | None = None
    # Inline content (v2 only)
    photos: list[PhotoContent] = []
    answers: list[AnswerContent] = []
    user_id: str | None = None


class UserProfileV2(BaseHingeModel):
    """Schema for v2 public profile (profile + content in one response).

    ``GET /user/v2/public?ids=`` returns demographics, photos, and answers
    in a single call.  Lacks pHash, voice waveform, videoPrompt, and
    promptPoll metadata that ``/content/v2/public`` provides.
    """

    identity_id: str
    profile: ProfileV2


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
    question_id: QuestionId
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


# --- New models from architect spec ---


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
