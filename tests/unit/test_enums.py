"""Unit tests for ``hinge.enums`` protocol enums.

Covers the concrete member values of every protocol enum
(``RatingAction``, ``RatingInitiatedWith``, ``FeedOrigin``, ``GenderEnum``,
``GenderPreferences``, ``ContentType``) plus the ``ContentType._missing_``
fallback that accepts unknown strings gracefully. Pure in-process tests, no
HTTP or I/O.
"""

from enum import Enum, IntEnum

import pytest

from hinge.enums import (
    ContentType,
    FeedOrigin,
    GenderEnum,
    GenderPreferences,
    RatingAction,
    RatingInitiatedWith,
)


# --- RatingAction -----------------------------------------------------------


def test_rating_action_values():
    assert RatingAction.BLOCK.value == "block"
    assert RatingAction.LIKE.value == "like"
    assert RatingAction.NOTE.value == "note"
    assert RatingAction.SKIP.value == "skip"
    assert RatingAction.REPORT.value == "report"


def test_rating_action_is_str_enum():
    assert issubclass(RatingAction, str)
    assert issubclass(RatingAction, Enum)
    # str-enum members compare equal to their raw string value.
    assert RatingAction.LIKE == "like"


def test_rating_action_lookup_by_value():
    assert RatingAction("skip") is RatingAction.SKIP


def test_rating_action_member_set():
    assert {m.value for m in RatingAction} == {
        "block",
        "like",
        "note",
        "skip",
        "report",
    }


def test_rating_action_unknown_value_raises():
    with pytest.raises(ValueError):
        RatingAction("nope")


# --- RatingInitiatedWith ----------------------------------------------------


def test_rating_initiated_with_values():
    assert RatingInitiatedWith.STANDARD.value == "standard"
    assert RatingInitiatedWith.SUPERLIKE.value == "superlike"


def test_rating_initiated_with_lookup_and_members():
    assert RatingInitiatedWith("superlike") is RatingInitiatedWith.SUPERLIKE
    assert {m.value for m in RatingInitiatedWith} == {"standard", "superlike"}


def test_rating_initiated_with_unknown_raises():
    with pytest.raises(ValueError):
        RatingInitiatedWith("ultralike")


# --- FeedOrigin -------------------------------------------------------------


def test_feed_origin_values():
    assert FeedOrigin.COMPATIBLES.value == "compatibles"
    assert FeedOrigin.ACTIVE_LATELY.value == "active_lately"
    assert FeedOrigin.NEARBY.value == "nearby"
    assert FeedOrigin.NEW_HERE.value == "new_here"
    assert FeedOrigin.STANDOUTS.value == "standouts"


def test_feed_origin_is_str_enum_and_members():
    assert issubclass(FeedOrigin, str)
    assert FeedOrigin("nearby") is FeedOrigin.NEARBY
    assert {m.value for m in FeedOrigin} == {
        "compatibles",
        "active_lately",
        "nearby",
        "new_here",
        "standouts",
    }


def test_feed_origin_unknown_raises():
    with pytest.raises(ValueError):
        FeedOrigin("explore")


# --- GenderEnum -------------------------------------------------------------


def test_gender_enum_values():
    assert GenderEnum.MEN.value == 0
    assert GenderEnum.WOMEN.value == 1
    assert GenderEnum.NON_BINARY.value == 3


def test_gender_enum_is_int_enum():
    assert issubclass(GenderEnum, IntEnum)
    # int-enum members behave as plain ints.
    assert GenderEnum.MEN == 0
    assert int(GenderEnum.NON_BINARY) == 3


def test_gender_enum_lookup_and_members():
    assert GenderEnum(1) is GenderEnum.WOMEN
    assert {m.value for m in GenderEnum} == {0, 1, 3}


def test_gender_enum_unknown_raises():
    with pytest.raises(ValueError):
        GenderEnum(2)


# --- GenderPreferences ------------------------------------------------------


def test_gender_preferences_values():
    assert GenderPreferences.OPEN_TO_ALL.value == -1
    assert GenderPreferences.MEN.value == 0
    assert GenderPreferences.WOMEN.value == 1
    assert GenderPreferences.NON_BINARY_PEOPLE.value == 3


def test_gender_preferences_open_to_all_lookup():
    assert GenderPreferences(-1) is GenderPreferences.OPEN_TO_ALL
    assert GenderPreferences.OPEN_TO_ALL == -1


def test_gender_preferences_members():
    assert {m.value for m in GenderPreferences} == {-1, 0, 1, 3}


def test_gender_preferences_unknown_raises():
    with pytest.raises(ValueError):
        GenderPreferences(99)


# --- ContentType: known members ---------------------------------------------


def test_content_type_values():
    assert ContentType.MEDIA.value == "media"
    assert ContentType.VOICE.value == "voice"
    assert ContentType.VIDEO.value == "video"
    assert ContentType.TEXT.value == "text"
    assert ContentType.POLL.value == "poll"
    assert ContentType.IDEA.value == "idea"


def test_content_type_known_lookup_returns_canonical_member():
    member = ContentType("media")
    assert member is ContentType.MEDIA
    assert member.name == "MEDIA"
    assert "media" in {m.value for m in ContentType}


def test_content_type_declared_members():
    assert {m.value for m in ContentType} == {
        "media",
        "voice",
        "video",
        "text",
        "poll",
        "idea",
    }


# --- ContentType: _missing_ fallback ----------------------------------------


def test_content_type_unknown_string_is_accepted():
    unknown = ContentType("hologram")

    assert isinstance(unknown, ContentType)
    assert unknown.value == "hologram"
    # Name is the upper-cased raw value per ``_missing_``.
    assert unknown.name == "HOLOGRAM"
    # str-subclass identity still holds.
    assert unknown == "hologram"


def test_content_type_unknown_not_registered_as_member():
    ContentType("ephemeral")

    # The fallback object is synthesised on the fly, not added to the enum.
    assert "EPHEMERAL" not in ContentType.__members__
    assert "ephemeral" not in {m.value for m in ContentType}


def test_content_type_unknown_creates_fresh_object_each_call():
    first = ContentType("transient")
    second = ContentType("transient")

    # Synthesised fallbacks are not cached/singletons.
    assert first is not second
    assert first == second  # equal as plain strings


def test_content_type_missing_coerces_non_string_value():
    # ``_missing_`` stringifies arbitrary values before constructing.
    coerced = ContentType(123)

    assert isinstance(coerced, ContentType)
    assert coerced.value == "123"
    assert coerced.name == "123"
    assert coerced == "123"


def test_content_type_missing_called_directly():
    obj = ContentType._missing_("gif")

    assert isinstance(obj, ContentType)
    assert obj.value == "gif"
    assert obj.name == "GIF"
