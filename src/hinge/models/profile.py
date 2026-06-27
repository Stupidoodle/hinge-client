"""User profile schemas (v2/v3 public profiles and the self-profile)."""

from datetime import datetime

from pydantic import Field

from hinge.models.attributes import (
    ChildrenStatus,
    DatingIntention,
    DrinkingStatus,
    DrugStatus,
    Educations,
    Ethnicities,
    FamilyPlans,
    GenderIdentity,
    HomeTown,
    JobTitle,
    Language,
    MarijuanaStatus,
    Pets,
    Politics,
    RelationshipType,
    Religion,
    SexualOrientation,
    SmokingStatus,
    Works,
)
from hinge.models.base import BaseHingeModel
from hinge.models.content import AnswerContent, PhotoContent


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
