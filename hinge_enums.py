"""Enums used in the Hinge API."""

from enum import Enum, IntEnum
from typing import Type

from pydantic_core import CoreSchema, core_schema


def add_base_preferences(cls: Type[IntEnum]):
    """Recreates an IntEnum using the functional API to add base members and methods."""
    members = {name: member.value for name, member in cls.__members__.items()}

    members["UNKNOWN"] = 99999999
    members["OPEN_TO_ALL"] = -1
    members["PREFER_NOT_TO_SAY"] = 0

    new_cls = IntEnum(cls.__name__, members)  # type: ignore

    @classmethod  # type: ignore # noqa
    def _missing_(cls_ref, value):
        """Handle any value not defined in the enum by returning UNKNOWN."""
        print(
            f"⚠️ Warning: Invalid value '{value}' for {cls_ref.__name__}. "
            f"Defaulting to UNKNOWN."
        )
        return cls_ref.UNKNOWN

    @classmethod  # type: ignore # noqa
    def __get_pydantic_core_schema__(cls_ref, source_type, handler) -> CoreSchema:
        """Generate a Pydantic core schema that allows validation from integers."""
        return core_schema.no_info_plain_validator_function(cls_ref)

    new_cls._missing_ = _missing_  # type: ignore
    new_cls.__get_pydantic_core_schema__ = __get_pydantic_core_schema__  # type: ignore

    return new_cls


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


class GenderPreferences(IntEnum):
    """Enum for gender preferences in user settings."""

    MEN = 0
    WOMEN = 1
    NON_BINARY_PEOPLE = 3
