"""Hinge like limit value object."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class HingeLikeLimit:
    """Current like/superlike limits."""

    likes_left: int
    superlikes_left: int
    free_superlikes_left: int | None = None
    free_superlike_expiration: datetime | None = None
