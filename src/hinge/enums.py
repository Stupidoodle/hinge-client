"""Enums used in the Hinge API."""

from enum import Enum, IntEnum

from pydantic_core import CoreSchema, core_schema


def add_base_preferences(cls: type[IntEnum]):
    """Recreate an IntEnum using the functional API to add base members and methods."""
    members = {name: member.value for name, member in cls.__members__.items()}

    members["UNKNOWN"] = 99999999
    members["OPEN_TO_ALL"] = -1
    members["PREFER_NOT_TO_SAY"] = 0

    new_cls = IntEnum(cls.__name__, members)  # type: ignore

    @classmethod  # type: ignore # noqa
    def _missing_(cls_ref, value):
        """Handle any value not defined in the enum by returning UNKNOWN."""
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
    LONG_TERM = 2
    LONG_TERM_OPEN_TO_SHORT = 3
    SHORT_TERM_OPEN_TO_LONG = 4
    SHORT_TERM_FUN = 5
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

    BUDDHIST = 1
    CATHOLIC = 2
    CHRISTIAN = 3
    HINDU = 4
    JEWISH = 5
    MUSLIM = 6
    SPIRITUAL = 7
    AGNOSTIC = 8
    ATHEIST = 9
    OTHER = 10
    SIKH = 11


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


@add_base_preferences
class FamilyPlansEnum(IntEnum):
    """Family plans codes used in Hinge."""

    DOESNT_WANT = 1
    WANTS = 2
    OPEN_TO = 3
    NOT_SURE_YET = 4


@add_base_preferences
class PetsEnum(IntEnum):
    """Pets codes used in Hinge."""

    BIRD = 1
    CAT = 2
    DOG = 3
    FISH = 4
    REPTILE = 5


class ZodiacEnum(IntEnum):
    """Zodiac sign codes used in Hinge."""

    ARIES = 1
    TAURUS = 2
    GEMINI = 3
    CANCER = 4
    LEO = 5
    VIRGO = 6
    LIBRA = 7
    SCORPIO = 8
    SAGITTARIUS = 9
    CAPRICORN = 10
    AQUARIUS = 11
    PISCES = 12


class LastActiveStatusEnum(IntEnum):
    """Last active status codes used in Hinge."""

    ACTIVE_NOW = 1
    RECENTLY_ACTIVE = 2


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


class QuestionId(str, Enum):
    """Enum for Hinge question IDs."""

    DONT_HATE_ME_IF_I = "5b5799a05b162c2841794201"
    MY_LOVE_LANGUAGE_IS = "5be0789228fd883a24045da0"
    ID_FALL_FOR_YOU_IF = "5b57992f5b162c284179343a"
    WHAT_IF_I_TOLD_YOU_THAT = "5ae735fc636de0035ebc1977"
    DORKIEST_THING_ABOUT_ME = "5b16da2b636de0035ea7e43a"
    WELL_GET_ALONG_IF = "5ae73690636de0035ebc2238"
    WE_ARE_SAME_WEIRD = "5cc8753228fd883a24ea9ff4"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        """Handle missing values gracefully."""
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
            self.UNKNOWN: "Unknown Question",
        }[self]

    @classmethod
    def get_dynamic_prompt_text(
        cls,
        question_id: str,
        prompt_lookup: dict[str, str] | None = None,
    ) -> str:
        """Resolve the display text for a question ID.

        ``prompt_lookup`` is the ``{question_id: text}`` dict provided by
        ``HingeApiAdapter._ensure_prompts()`` (DB-backed). Falls back to
        the hard-coded enum for legacy IDs that pre-date the dynamic
        catalog, and to "Unknown Question" otherwise.
        """
        if prompt_lookup is not None:
            text = prompt_lookup.get(question_id)
            if text is not None:
                return text

        try:
            return cls(question_id).prompt_text
        except ValueError:
            return "Unknown Question"

    @classmethod
    def get_all_available_prompts(
        cls,
        prompt_lookup: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Return every known prompt as a ``{id: text}`` dict.

        Prefers the dynamic catalog when supplied, otherwise falls back
        to the hard-coded enum members.
        """
        if prompt_lookup is not None:
            return dict(prompt_lookup)

        return {
            member.value: member.prompt_text for member in cls if member != cls.UNKNOWN
        }


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


@add_base_preferences
class GenderPreferences(IntEnum):
    """Enum for gender preferences in user settings."""

    MEN = 0
    WOMEN = 1
    NON_BINARY_PEOPLE = 3
