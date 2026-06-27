"""Shared base model for Hinge API schemas."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseHingeModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="ignore",
        populate_by_name=True,
    )
