"""Profile and vital attribute sub-models for Hinge API schemas.

These wrap the per-field ``value``/``visible`` shape returned by the
``/user/v3`` endpoint, plus the shared ``BoundingBox`` geometry sub-model
referenced by photo, prompt, and standout content.
"""

from hinge.models.base import BaseHingeModel


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


class BoundingBox(BaseHingeModel):
    """Schema for bounding box coordinates within a photo."""

    top_left: dict[str, float]
    bottom_right: dict[str, float]
