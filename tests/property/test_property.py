"""Hypothesis property tests for the static catalog and protocol enums.

These exercise invariants over *real* bundled data (``hinge/data/catalog.json``)
and the code-level protocol enums in :mod:`hinge.enums`. Everything is offline,
bounded and deterministic: strategies only sample from finite real data or from
plain text, and ``derandomize`` pins example generation.
"""

from enum import IntEnum

from hypothesis import given, settings
from hypothesis import strategies as st

from hinge.core.catalog import EnumCatalog
from hinge.enums import (
    ContentType,
    FeedOrigin,
    GenderEnum,
    GenderPreferences,
    RatingAction,
    RatingInitiatedWith,
)

# Deterministic, fast: no timing-based flakiness, fixed example generation.
DETERMINISTIC = settings(deadline=None, derandomize=True, max_examples=300)

# Load the real bundled catalog once; build a flat list of every (attr, id, label).
CATALOG = EnumCatalog.load()
PAIRS = [
    (attr, ordinal, label)
    for attr in CATALOG.attributes()
    for ordinal, label in CATALOG.labels(attr).items()
]


@st.composite
def randomly_cased_pair(draw):
    """A real (attr, ordinal, label) triple with the label's case scrambled."""
    attr, ordinal, label = draw(st.sampled_from(PAIRS))
    mask = draw(st.lists(st.booleans(), min_size=len(label), max_size=len(label)))
    cased = "".join(
        ch.upper() if flip else ch.lower() for ch, flip in zip(label, mask, strict=True)
    )
    return attr, ordinal, cased


# --------------------------------------------------------------------------- #
# EnumCatalog: ordinal <-> label round-trips over the real data
# --------------------------------------------------------------------------- #


def test_catalog_has_data():
    """Sanity guard so the property tests below are not vacuous."""
    assert PAIRS
    assert len(CATALOG.attributes()) > 1


@DETERMINISTIC
@given(st.sampled_from(PAIRS))
def test_ordinal_label_ordinal_roundtrip(triple):
    """``ordinal -> label -> ordinal`` returns the original ordinal."""
    attr, ordinal, _label = triple
    label = CATALOG.label(attr, ordinal)
    assert label is not None
    assert CATALOG.ordinal(attr, label) == ordinal


@DETERMINISTIC
@given(st.sampled_from(PAIRS))
def test_label_ordinal_label_roundtrip(triple):
    """``label -> ordinal -> label`` returns the original label."""
    attr, _ordinal, label = triple
    ordinal = CATALOG.ordinal(attr, label)
    assert ordinal is not None
    assert CATALOG.label(attr, ordinal) == label


@DETERMINISTIC
@given(randomly_cased_pair())
def test_ordinal_lookup_is_case_insensitive(triple):
    """Label -> ordinal resolution ignores case for every real label."""
    attr, ordinal, cased_label = triple
    assert CATALOG.ordinal(attr, cased_label) == ordinal


@DETERMINISTIC
@given(st.sampled_from(PAIRS))
def test_label_is_marked_valid(triple):
    """Every shipped ordinal is reported valid for its attribute."""
    attr, ordinal, _label = triple
    assert CATALOG.is_valid(attr, ordinal)


@DETERMINISTIC
@given(st.sampled_from(CATALOG.attributes()), st.text())
def test_ordinal_of_unknown_label_is_none(attr, label):
    """Labels that are not in the catalog resolve to ``None``."""
    known = {lbl.casefold() for lbl in CATALOG.labels(attr).values()}
    if label.casefold() in known:
        # A real label round-trips to a real ordinal instead.
        assert CATALOG.ordinal(attr, label) is not None
    else:
        assert CATALOG.ordinal(attr, label) is None


# --------------------------------------------------------------------------- #
# ContentType._missing_: accepts arbitrary strings
# --------------------------------------------------------------------------- #

KNOWN_CONTENT_VALUES = frozenset(member.value for member in ContentType)


@DETERMINISTIC
@given(st.text())
def test_content_type_accepts_any_string(value):
    """``ContentType(s)`` never raises and equals its input string."""
    ct = ContentType(value)
    assert isinstance(ct, ContentType)
    assert isinstance(ct, str)
    assert ct == value


@DETERMINISTIC
@given(st.text().filter(lambda s: s not in KNOWN_CONTENT_VALUES))
def test_content_type_missing_branch(value):
    """Unknown strings flow through ``_missing_`` with derived name/value."""
    ct = ContentType(value)
    assert ct.value == value
    assert ct.name == value.upper()
    assert ct == value
    # Pseudo-members are never registered: the canonical set stays at six.
    assert len(list(ContentType)) == len(KNOWN_CONTENT_VALUES)


@DETERMINISTIC
@given(st.sampled_from(sorted(KNOWN_CONTENT_VALUES)))
def test_content_type_known_values_are_canonical(value):
    """Known values resolve to the singleton member, not a pseudo-member."""
    ct = ContentType(value)
    assert ct is ContentType(value)
    assert ct in list(ContentType)
    assert ct.value == value


# --------------------------------------------------------------------------- #
# Protocol enums: value stability
# --------------------------------------------------------------------------- #

PROTOCOL_ENUMS = (
    RatingAction,
    RatingInitiatedWith,
    FeedOrigin,
    GenderEnum,
    GenderPreferences,
    ContentType,
)
PROTOCOL_MEMBERS = [member for enum in PROTOCOL_ENUMS for member in enum]

# Pinned wire values: a rename here is a breaking protocol change and must fail.
PINNED_VALUES = [
    (RatingAction.BLOCK, "block"),
    (RatingAction.LIKE, "like"),
    (RatingAction.NOTE, "note"),
    (RatingAction.SKIP, "skip"),
    (RatingAction.REPORT, "report"),
    (RatingInitiatedWith.STANDARD, "standard"),
    (RatingInitiatedWith.SUPERLIKE, "superlike"),
    (FeedOrigin.COMPATIBLES, "compatibles"),
    (FeedOrigin.ACTIVE_LATELY, "active_lately"),
    (FeedOrigin.NEARBY, "nearby"),
    (FeedOrigin.NEW_HERE, "new_here"),
    (FeedOrigin.STANDOUTS, "standouts"),
    (GenderEnum.MEN, 0),
    (GenderEnum.WOMEN, 1),
    (GenderEnum.NON_BINARY, 3),
    (GenderPreferences.OPEN_TO_ALL, -1),
    (GenderPreferences.MEN, 0),
    (GenderPreferences.WOMEN, 1),
    (GenderPreferences.NON_BINARY_PEOPLE, 3),
    (ContentType.MEDIA, "media"),
    (ContentType.VOICE, "voice"),
    (ContentType.VIDEO, "video"),
    (ContentType.TEXT, "text"),
    (ContentType.POLL, "poll"),
    (ContentType.IDEA, "idea"),
]


@DETERMINISTIC
@given(st.sampled_from(PROTOCOL_MEMBERS))
def test_protocol_member_roundtrips_by_value_and_name(member):
    """Each member is recoverable from its own value and name."""
    cls = type(member)
    assert cls(member.value) is member
    assert cls[member.name] is member


@DETERMINISTIC
@given(st.sampled_from(PROTOCOL_MEMBERS))
def test_protocol_member_value_type_is_stable(member):
    """Int enums carry int values; string enums carry str values."""
    if isinstance(member, IntEnum):
        assert isinstance(member.value, int)
    else:
        assert isinstance(member.value, str)


@DETERMINISTIC
@given(st.sampled_from(PINNED_VALUES))
def test_protocol_pinned_wire_values(pair):
    """Pinned wire values never drift from their documented constants."""
    member, expected = pair
    assert member.value == expected
    assert member == expected
