"""User preference and dealbreaker schemas for Hinge API requests."""

from pydantic import Field, model_validator

from hinge.models.base import BaseHingeModel


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
    gender_preferences: list[int] = Field(
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
