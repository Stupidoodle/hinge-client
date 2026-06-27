"""Unit tests for pydantic schemas in :mod:`hinge.models`.

Covers camelCase<->snake alias round-trips, the
``Preferences.validate_dealbreakers`` rules, the ``AnswerContent`` field
validators, the ``CreateRateContent.check_photo_or_prompt`` validator, and the
tolerant ``ContentType._missing_`` enum hook. Everything here is offline and
deterministic — synthetic data only.
"""

import pytest
from pydantic import ValidationError

from hinge.enums import ContentType
from hinge.models import (
    AnswerContent,
    ContentSettings,
    CreateRateContent,
    CreateRateContentPrompt,
    Dealbreakers,
    GenderedDealbreaker,
    GenderedRange,
    LikeLimit,
    Preferences,
    RangeDetails,
    RatePhoto,
    TranscriptionMetadata,
)

# ---------------------------------------------------------------------------
# alias round-trips
# ---------------------------------------------------------------------------


def test_generated_camel_alias_round_trip():
    """to_camel-generated aliases survive a by_alias dump + re-validate cycle."""
    settings = ContentSettings(
        is_smart_photo_opt_in=True,
        is_convo_starters_opt_in=False,
    )

    dumped = settings.model_dump(by_alias=True)
    assert dumped == {
        "isSmartPhotoOptIn": True,
        "isConvoStartersOptIn": False,
    }

    # Re-parsing the camelCase payload reconstructs an equal model.
    assert ContentSettings.model_validate(dumped) == settings


def test_populate_by_name_accepts_snake_case():
    """populate_by_name=True lets the snake_case field names be used directly."""
    by_name = ContentSettings.model_validate(
        {"is_smart_photo_opt_in": True, "is_convo_starters_opt_in": True},
    )
    assert by_name.is_smart_photo_opt_in is True
    assert by_name.is_convo_starters_opt_in is True

    # The snake-keyed dump is the non-aliased view.
    assert by_name.model_dump() == {
        "is_smart_photo_opt_in": True,
        "is_convo_starters_opt_in": True,
    }


def test_explicit_alias_overrides_generator():
    """An explicit Field(alias=...) wins over the to_camel generator."""
    limit = LikeLimit(likes_left=5, super_likes_left=2)

    dumped = limit.model_dump(by_alias=True)
    # likes_left -> generated camelCase; super_likes_left -> explicit alias.
    assert dumped["likesLeft"] == 5
    assert dumped["superlikesLeft"] == 2
    assert "superLikesLeft" not in dumped

    # The explicit alias also feeds validation round-trips.
    assert LikeLimit.model_validate(dumped) == limit


def test_numeric_string_aliases_round_trip():
    """Gendered ranges use "0"/"1"/"3" aliases that survive a round-trip."""
    rng = GenderedRange(men=RangeDetails(min=18, max=30))

    dumped = rng.model_dump(by_alias=True)
    assert dumped["0"] == {"max": 30, "min": 18}
    assert dumped["1"] is None
    assert dumped["3"] is None

    parsed = GenderedRange.model_validate(dumped)
    assert parsed.men == RangeDetails(min=18, max=30)
    assert parsed.women is None
    assert parsed.non_binary_people is None


# ---------------------------------------------------------------------------
# Preferences.validate_dealbreakers
# ---------------------------------------------------------------------------


def _make_dealbreakers(**overrides: bool) -> Dealbreakers:
    base: dict[str, object] = {
        "marijuana": False,
        "smoking": False,
        "max_distance": False,
        "drinking": False,
        "education_attained": False,
        "gendered_height": GenderedDealbreaker(),
        "politics": False,
        "relationship_types": False,
        "drugs": False,
        "dating_intentions": False,
        "family_plans": False,
        "gendered_age": GenderedDealbreaker(),
        "religions": False,
        "ethnicities": False,
        "children": False,
    }
    base.update(overrides)
    return Dealbreakers(**base)


def _make_prefs(dealbreakers: Dealbreakers | None = None, **overrides) -> Preferences:
    base: dict[str, object] = {
        "gendered_age_ranges": GenderedRange(),
        "dealbreakers": dealbreakers or _make_dealbreakers(),
        "religions": [],
        "drinking": [],
        "gendered_height_ranges": GenderedRange(),
        "marijuana": [],
        "relationship_types": [],
        "drugs": [],
        "max_distance": 50,
        "children": [],
        "ethnicities": [],
        "smoking": [],
        "education_attained": [],
        "family_plans": [],
        "dating_intentions": [],
        "politics": [],
        "gender_preferences": [1],
    }
    base.update(overrides)
    return Preferences(**base)


def test_preferences_valid_baseline():
    """A baseline with empty option lists passes the dealbreaker validator."""
    prefs = _make_prefs()
    assert prefs.max_distance == 50
    assert prefs.gender_preferences == [1]


def test_preferences_open_to_all_alone_is_ok():
    """A lone -1 (OPEN_TO_ALL) with the matching dealbreaker False is allowed."""
    prefs = _make_prefs(religions=[-1])
    assert prefs.religions == [-1]


def test_preferences_zero_prefer_not_to_say_rejected():
    """A 0 value (PREFER_NOT_TO_SAY) inside an option list is rejected."""
    with pytest.raises(ValidationError) as exc:
        _make_prefs(religions=[0])
    assert "PREFER_NOT_TO_SAY" in str(exc.value)
    assert "religions" in str(exc.value)


def test_preferences_open_to_all_with_other_values_rejected():
    """-1 (OPEN_TO_ALL) cannot be combined with any other option value."""
    with pytest.raises(ValidationError) as exc:
        _make_prefs(religions=[-1, 7])
    assert "OPEN_TO_ALL" in str(exc.value)
    assert "have other values" in str(exc.value)


def test_preferences_open_to_all_with_dealbreaker_true_rejected():
    """-1 (OPEN_TO_ALL) cannot pair with that field set True in dealbreakers."""
    with pytest.raises(ValidationError) as exc:
        _make_prefs(dealbreakers=_make_dealbreakers(religions=True), religions=[-1])
    assert "OPEN_TO_ALL" in str(exc.value)
    assert "set to True in dealbreakers" in str(exc.value)


# ---------------------------------------------------------------------------
# AnswerContent validators
# ---------------------------------------------------------------------------


def _answer(**overrides) -> AnswerContent:
    base: dict[str, object] = {"content_id": "content-1", "question_id": "q-1"}
    base.update(overrides)
    return AnswerContent(**base)


def test_answer_empty_transcription_metadata_becomes_none():
    """An empty dict for transcription_metadata is coerced to None."""
    answer = _answer(transcription_metadata={})
    assert answer.transcription_metadata is None


def test_answer_explicit_none_transcription_metadata_kept():
    """A None transcription_metadata passes through unchanged."""
    answer = _answer(transcription_metadata=None)
    assert answer.transcription_metadata is None


def test_answer_non_empty_transcription_metadata_parsed():
    """A populated dict is parsed into a TranscriptionMetadata model."""
    answer = _answer(
        transcription_metadata={"content_id": "tm-1", "type": "voice"},
    )
    assert isinstance(answer.transcription_metadata, TranscriptionMetadata)
    assert answer.transcription_metadata.content_id == "tm-1"
    assert answer.transcription_metadata.type == "voice"


def test_answer_transcription_metadata_instance_passthrough():
    """An already-built TranscriptionMetadata instance is left untouched."""
    tm = TranscriptionMetadata(content_id="tm-2", type="video")
    answer = _answer(transcription_metadata=tm)
    assert answer.transcription_metadata is tm


def test_answer_transcription_string_kept():
    """A plain string transcription is preserved verbatim."""
    answer = _answer(transcription="spoken words here")
    assert answer.transcription == "spoken words here"


def test_answer_transcription_none_kept():
    """A None transcription passes through the coercion unchanged."""
    answer = _answer(transcription=None)
    assert answer.transcription is None


def test_answer_transcription_dict_transcript_key():
    """A dict with a 'transcript' key is reduced to that value."""
    answer = _answer(transcription={"transcript": "from transcript"})
    assert answer.transcription == "from transcript"


def test_answer_transcription_dict_transcription_fallback():
    """An empty 'transcript' falls back to the 'transcription' key."""
    answer = _answer(
        transcription={"transcript": "", "transcription": "from fallback"},
    )
    assert answer.transcription == "from fallback"


def test_answer_transcription_dict_missing_keys_becomes_empty():
    """A dict with neither known key collapses to an empty string."""
    answer = _answer(transcription={"unrelated": "value"})
    assert answer.transcription == ""


# ---------------------------------------------------------------------------
# CreateRateContent.check_photo_or_prompt
# ---------------------------------------------------------------------------


def _photo() -> RatePhoto:
    return RatePhoto(content_id="c-1", url="https://cdn.example/p.jpg", cdn_id="cdn-1")


def _prompt() -> CreateRateContentPrompt:
    return CreateRateContentPrompt(
        answer="my answer",
        content_id="pc-1",
        question="my question",
    )


def test_create_rate_content_photo_only_ok():
    """A photo-only content payload validates."""
    content = CreateRateContent(comment="hi", photo=_photo())
    assert content.photo is not None
    assert content.prompt is None


def test_create_rate_content_prompt_only_ok():
    """A prompt-only content payload validates."""
    content = CreateRateContent(prompt=_prompt())
    assert content.prompt is not None
    assert content.photo is None


def test_create_rate_content_neither_rejected():
    """Neither photo nor prompt set is rejected."""
    with pytest.raises(ValidationError) as exc:
        CreateRateContent(comment="just a comment")
    assert "must be set" in str(exc.value)


def test_create_rate_content_both_rejected():
    """Setting both photo and prompt is rejected."""
    with pytest.raises(ValidationError) as exc:
        CreateRateContent(photo=_photo(), prompt=_prompt())
    assert "cannot both be set" in str(exc.value)


# ---------------------------------------------------------------------------
# ContentType._missing_
# ---------------------------------------------------------------------------


def test_content_type_known_value_is_canonical_member():
    """A known value resolves to the declared enum member (no _missing_)."""
    assert ContentType("media") is ContentType.MEDIA
    assert ContentType.VOICE.value == "voice"


def test_content_type_unknown_value_tolerated():
    """An unknown value is accepted via _missing_ as a synthetic member."""
    unknown = ContentType("hologram")
    assert isinstance(unknown, ContentType)
    assert unknown.value == "hologram"
    assert unknown.name == "HOLOGRAM"
    # str-enum equality still works against the raw string.
    assert unknown == "hologram"
