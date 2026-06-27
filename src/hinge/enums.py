"""Protocol enums for the Hinge API.

Only stable, code-level protocol values live here. Display-catalogue values
(religion, ethnicity, language, dating intention, …) are data, not enums — they
are resolved at runtime via :mod:`hinge.core.catalog`.
"""

from enum import Enum, IntEnum


class RatingAction(str, Enum):
    """Rating action types for the /rate/v2/initiate endpoint."""

    BLOCK = "block"
    LIKE = "like"
    NOTE = "note"
    SKIP = "skip"
    REPORT = "report"


class RatingInitiatedWith(str, Enum):
    """Rating initiated-with type for superlike vs standard."""

    STANDARD = "standard"
    SUPERLIKE = "superlike"


class FeedOrigin(str, Enum):
    """Feed origin types from the recommendation endpoint."""

    COMPATIBLES = "compatibles"
    ACTIVE_LATELY = "active_lately"
    NEARBY = "nearby"
    NEW_HERE = "new_here"
    STANDOUTS = "standouts"


class GenderEnum(IntEnum):
    """Gender codes used in Hinge."""

    MEN = 0
    WOMEN = 1
    NON_BINARY = 3


class GenderPreferences(IntEnum):
    """Gender preference selections in user settings (``-1`` = open to all)."""

    OPEN_TO_ALL = -1
    MEN = 0
    WOMEN = 1
    NON_BINARY_PEOPLE = 3


class ContentType(str, Enum):
    """Supported content types for prompts."""

    MEDIA = "media"
    VOICE = "voice"
    VIDEO = "video"
    TEXT = "text"
    POLL = "poll"
    IDEA = "idea"

    @classmethod
    def _missing_(cls, value: object) -> ContentType:
        """Accept unknown content types gracefully."""
        obj = str.__new__(cls, str(value))
        obj._name_ = str(value).upper()
        obj._value_ = str(value)
        return obj
