"""Pydantic schemas for API responses.

The holy texts. Parsing this much JSON without Pydantic is a war crime.
"""

from datetime import datetime
from enum import Enum, IntEnum
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class BaseHingeModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="ignore",
        populate_by_name=True,
    )


def add_base_preferences(cls):
    """Add common preferences via decorator and a _missing_ method to an Enum."""
    # Add common members to the enum's namespace
    cls.UNKNOWN = 99999999
    cls.OPEN_TO_ALL = -1
    cls.PREFER_NOT_TO_SAY = 0

    # Define the _missing_ method
    def _missing_(value):
        """Handle missing values gracefully."""
        if value is None:
            return cls.UNKNOWN
        print(
            f"⚠️ Warning: Invalid value '{value}' for {cls.__name__}. "
            f"Defaulting to UNKNOWN."
        )
        return cls.UNKNOWN

    # Add the method to the class, making it a classmethod
    cls._missing_ = classmethod(_missing_)

    return cls


@add_base_preferences
class ChildrenStatusEnum(IntEnum):
    """Children status codes used in Hinge."""

    NO = 1
    YES = 2


@add_base_preferences
class DatingIntentionEnum(IntEnum):
    """Dating intention codes used in Hinge."""

    LIFE_PARTNER = 1
    FIGURING_OUT_GOALS = 6


@add_base_preferences
class DrinkingStatusEnum(IntEnum):
    """Drinking status codes used in Hinge."""

    YES = 1
    SOMETIMES = 2
    NO = 3


@add_base_preferences
class DrugStatusEnum(IntEnum):
    """Drug usage status codes used in Hinge."""

    YES = 1
    SOMETIMES = 2
    NO = 3


@add_base_preferences
class SmokingStatusEnum(IntEnum):
    """Smoking status codes used in Hinge."""

    YES = 1
    SOMETIMES = 2
    NO = 3


@add_base_preferences
class MarijuanaStatusEnum(IntEnum):
    """Marijuana usage status codes used in Hinge."""

    YES = 1
    SOMETIMES = 2
    NO = 3


@add_base_preferences
class EducationAttainedEnum(IntEnum):
    """Education levels used in Hinge."""

    SECONDARY_SCHOOL = 1
    UNDERGRAD = 2
    POSTGRAD = 3


@add_base_preferences
class ReligionEnum(IntEnum):
    """Religion codes used in Hinge."""

    CATHOLIC = 2
    CHRISTIAN = 3
    MUSLIM = 6


@add_base_preferences
class PoliticsEnum(IntEnum):
    """Political orientation codes used in Hinge."""

    LIBERAL = 1
    MODERATE = 2
    CONSERVATIVE = 3
    NOT_POLITICAL = 4
    OTHER = 5


@add_base_preferences
class RelationshipTypeEnum(IntEnum):
    """Relationship type codes used in Hinge."""

    MONOGAMY = 1
    NON_MONOGAMY = 2
    FIGURING_OUT = 3


@add_base_preferences
class LanguageEnum(IntEnum):
    """Language codes used in Hinge."""

    ENGLISH = 26
    GERMAN = 36
    VIETNAMESE = 126
    FRENCH = 32
    SPANISH = 108


@add_base_preferences
class EthnicitiesEnum(IntEnum):
    """Ethnicity codes used in Hinge."""

    NATIVE_AMERICAN = 1
    BLACK_AFRICAN = 2
    EAST_ASIAN = 3
    HISPANIC_LATINO = 4
    MIDDLE_EASTERN = 5
    PACIFIC_ISLANDER = 6
    SOUTH_ASIAN = 7
    WHITE_CAUCASIAN = 8
    OTHER = 9
    SOUTHEAST_ASIAN = 10


class QuestionId(str, Enum):
    """Enum for Hinge question IDs."""

    DONT_HATE_ME_IF_I = "5b5799a05b162c2841794201"  # "Don't hate me if I"
    MY_LOVE_LANGUAGE_IS = "5be0789228fd883a24045da0"  # "My Love Language is"
    ID_FALL_FOR_YOU_IF = "5b57992f5b162c284179343a"  # "I'd fall for you if"
    WHAT_IF_I_TOLD_YOU_THAT = "5ae735fc636de0035ebc1977"  # "What if I told you that"
    DORKIEST_THING_ABOUT_ME = (
        "5b16da2b636de0035ea7e43a"  # "The dorkiest thing about me is"
    )
    WELL_GET_ALONG_IF = "5ae73690636de0035ebc2238"  # "We'll get along if"
    WE_ARE_SAME_WEIRD = "5cc8753228fd883a24ea9ff4"  # "We're the same type of weird if"
    UNKNOWN = "unknown"  # Fallback for missing values

    @classmethod
    def _missing_(cls, value):
        """Handle missing values gracefully."""
        print(
            f"Warning: Missing QuestionId value for {value}. "
            f"Defaulting to UNKNOWN."
        )
        return cls.UNKNOWN

    @property
    def prompt_text(self) -> str:
        """Return the prompt text associated with the question ID."""
        return {
            self.DONT_HATE_ME_IF_I: "Don't hate me if I",
            self.MY_LOVE_LANGUAGE_IS: "My Love Language is",
            self.ID_FALL_FOR_YOU_IF: "I'd fall for you if",
            self.WHAT_IF_I_TOLD_YOU_THAT: "What if I told you that",
            self.DORKIEST_THING_ABOUT_ME: "The dorkiest thing about me is",
            self.WELL_GET_ALONG_IF: "We'll get along if",
            self.WE_ARE_SAME_WEIRD: "We're the same type of weird if",
        }[self]


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


class GenderPreferences(IntEnum):
    """Enum for gender preferences in user settings."""

    MEN = 0
    WOMEN = 1
    NON_BINARY_PEOPLE = 3


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
    family_plans: list[int] | None = [-1]  # TODO: Define proper enum
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
    super_likes_left: int  # If you have those, consider yourself lost
    free_super_likes_left: int
    free_super_like_expiration: datetime | None = None


class TextReview(BaseHingeModel):
    """Schema for the text moderation pre-flight check."""

    is_harmful: bool


class RecommendationSubject(BaseHingeModel):
    """A single user recommendation from the feed."""

    subject_id: str
    rating_token: str


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
    children: ChildrenStatus | ChildrenStatusEnum | None = None  # Using new Enum
    dating_intention: DatingIntention | ChildrenStatusEnum | None = (
        None  # Using new Enum
    )
    dating_intention_text: str | None = None
    drinking: DrinkingStatus | DrinkingStatusEnum | None = None  # Using new Enum
    drugs: DrugStatus | DrugStatusEnum | None = None  # Using new Enum
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
    marijuana: MarijuanaStatus | None = None  # Using new Enum
    pets: Pets | list[int] | None = None
    politics: Politics | PoliticsEnum | None = None
    pronouns: list[int] | None = None
    relationship_type_ids: RelationshipType | list[RelationshipTypeEnum] | None = (
        None  # Using new Enum
    )
    relationship_types_text: str | None = None
    religions: Religion | ReligionEnum | None = None  # Using new Enum
    selfie_verified: bool | None = None
    sexual_orientations: SexualOrientation | list[int] | None = None
    smoking: SmokingStatus | SmokingStatusEnum | None = None
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


class PhotoContent(BaseHingeModel):
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


class Feedback(BaseHingeModel):
    """Schema for the feedback on a prompt."""

    evaluation: str | None = None
    detail: str | None = None
    feedback_token: str | None = None


class TranscriptionMetadata(BaseHingeModel):
    """Placeholder for transcription metadata."""

    pass


class TextAnswer(BaseHingeModel):
    """Schema for the text content of a prompt answer."""

    response: str
    question_id: str  # The questionId is duplicated here for some reason


class AnswerContentPayload(BaseHingeModel):
    """Schema for a single answer object in the PUT /content/v1/answers payload."""

    position: int
    question_id: QuestionId
    text_answer: TextAnswer


class AnswerContent(BaseHingeModel):
    """Schema for a prompt answer."""

    content_id: str
    position: int | None = None  # Added
    question_id: QuestionId
    type: str | None = None  # Added (e.g., 'text')
    response: str
    transcription_metadata: TranscriptionMetadata | None = None  # Added
    feedback: Feedback | None = None  # Added


class PromptContent(BaseHingeModel):
    """Schema for a user's prompt content."""

    content_id: str
    question_id: QuestionId
    options: list[str]


class ProfileContent(BaseHingeModel):
    """Schema for a user's full content (photos, answers, etc.)."""

    user_id: str
    content: dict[str, list[PhotoContent | AnswerContent] | PromptContent]


class SelfContentResponse(BaseHingeModel):
    """Schema for the authenticated user's content data (GET /content/v2)."""

    content: dict[str, list[PhotoContent | AnswerContent]]
