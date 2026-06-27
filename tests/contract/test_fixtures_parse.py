"""Contract tests: synthetic, schema-faithful payloads parse and round-trip.

Each major Hinge response model in :mod:`hinge.models` is fed a hand-written
JSON fixture (``tests/fixtures/*.json``) that mirrors the real API shape with
fabricated values only. For every model we assert that:

* the camelCase payload validates into the model, and
* a ``model_dump(by_alias=True)`` -> ``model_validate`` round-trip is stable
  (re-parsing the aliased dump reconstructs an equal model).

A handful of minimal/empty inline payloads exercise the default-and-missing
branches. Everything is offline and deterministic.
"""

from pydantic import BaseModel

from hinge.enums import ContentType
from hinge.models import (
    ChildrenStatus,
    LikeLimit,
    Preferences,
    PromptsResponse,
    RecommendationsResponse,
    Religion,
    SelfContentResponse,
    SelfProfileResponse,
    StandoutsV2Response,
    StandoutsV3Response,
    UserProfile,
    UserProfileV2,
)
from hinge.models.rating import LikesYouResponse
from tests.conftest import load_fixture


def _round_trips(model: BaseModel) -> bool:
    """The aliased dump re-validates into an equal model."""
    cls = type(model)
    re_parsed = cls.model_validate(model.model_dump(by_alias=True))
    return re_parsed == model


# --------------------------------------------------------------------------- #
# RecommendationsResponse
# --------------------------------------------------------------------------- #


def test_recommendations_response_parses():
    payload = load_fixture("recommendations_response.json")
    model = RecommendationsResponse.model_validate(payload)

    assert len(model.feeds) == 1
    feed = model.feeds[0]
    assert feed.origin == "compatibles"
    assert [s.subject_id for s in feed.subjects] == ["subject-aaa", "subject-bbb"]

    first, second = feed.subjects
    assert first.rating_token == "token-aaa"
    assert first.enhancements is not None
    assert first.enhancements.second_chance is not None
    assert first.enhancements.second_chance.second_chance_source == 2
    # The optional enhancements/origin default to None on the second subject.
    assert second.enhancements is None
    assert second.origin is None

    assert _round_trips(model)


def test_recommendations_response_empty_feeds():
    model = RecommendationsResponse.model_validate({"feeds": []})
    assert model.feeds == []
    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# SelfProfileResponse
# --------------------------------------------------------------------------- #


def test_self_profile_response_parses():
    payload = load_fixture("self_profile_response.json")
    model = SelfProfileResponse.model_validate(payload)

    assert model.user_id == "self-user-123"
    assert model.paused is False
    assert model.last_active_opt_in is True
    assert model.profile.first_name == "Robin"
    assert model.profile.location.name == "Boston"

    # v3 wrapper-dict branches resolve to the attribute sub-models.
    assert isinstance(model.profile.children, ChildrenStatus)
    assert model.profile.children.value == 0
    assert model.profile.children.visible is False
    assert isinstance(model.profile.religions, Religion)
    assert model.profile.religions.value == [1, 2]

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# UserProfile (v3 public)
# --------------------------------------------------------------------------- #


def test_user_profile_parses():
    payload = load_fixture("user_profile.json")
    model = UserProfile.model_validate(payload)

    assert model.user_id == "public-user-456"
    assert model.profile.first_name == "Sam"
    assert model.profile.location.metro_area == "New York City"
    # Explicit alias "didjustJoin" feeds the snake field.
    assert model.profile.did_just_join is False
    assert isinstance(model.profile.children, ChildrenStatus)
    assert model.profile.children.value == 1

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# UserProfileV2 (v2 inline: scalar/list union branches + photos/answers)
# --------------------------------------------------------------------------- #


def test_user_profile_v2_parses():
    payload = load_fixture("user_profile_v2.json")
    model = UserProfileV2.model_validate(payload)

    assert model.identity_id == "identity-v2-789"
    profile = model.profile
    assert profile.first_name == "Alex"
    assert profile.user_id == "public-user-789"
    assert profile.did_just_join is True

    # The v2 payload uses scalar / plain-list values, exercising the
    # non-wrapper branches of the attribute unions.
    assert profile.children == 2
    assert profile.dating_intention == 1
    assert profile.religions == [1, 2]
    assert profile.languages_spoken == [10, 20]
    assert profile.works == "Acme Corp"
    assert profile.hometown == "Boston, MA"

    # Inline content (v2 only).
    assert len(profile.photos) == 1
    photo = profile.photos[0]
    assert photo.cdn_id == "cdn-photo-1"
    assert photo.p_hash == "abc123"
    assert photo.bounding_box is not None
    assert photo.bounding_box.top_left == {"x": 0.1, "y": 0.1}
    assert len(photo.videos) == 1
    assert photo.videos[0].quality == "hd"

    assert len(profile.answers) == 1
    assert profile.answers[0].question_id == "question-1"
    assert profile.answers[0].response == "Two truths and a lie"

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# Preferences
# --------------------------------------------------------------------------- #


def test_preferences_parses():
    payload = load_fixture("preferences.json")
    model = Preferences.model_validate(payload)

    assert model.max_distance == 50
    assert model.gender_preferences == [1]
    assert model.religions == [1, 2]
    assert model.relationship_types == [6]

    # Numeric-string gendered aliases resolve to the named ranges.
    assert model.gendered_age_ranges.men is not None
    assert model.gendered_age_ranges.men.min == 24
    assert model.gendered_age_ranges.men.max == 35
    assert model.gendered_age_ranges.women is not None
    assert model.gendered_age_ranges.non_binary_people is None
    assert model.gendered_height_ranges.men is not None
    assert model.gendered_height_ranges.men.max == 76

    assert model.dealbreakers.gendered_age.men is True
    assert model.dealbreakers.children is False

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# PromptsResponse
# --------------------------------------------------------------------------- #


def test_prompts_response_parses():
    payload = load_fixture("prompts_response.json")
    model = PromptsResponse.model_validate(payload)

    assert len(model.prompts) == 2
    first, second = model.prompts
    assert first.id == "prompt-1"
    assert first.content_types == [ContentType.TEXT, ContentType.POLL]
    assert first.placeholder == "Go on..."
    # Defaults kick in for the sparse second prompt.
    assert second.placeholder == ""
    assert second.categories == []
    assert second.content_types == []

    assert len(model.categories) == 1
    assert model.categories[0].slug == "icebreakers"
    assert model.categories[0].is_visible is True

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# StandoutsV2Response
# --------------------------------------------------------------------------- #


def test_standouts_v2_response_parses():
    payload = load_fixture("standouts_v2_response.json")
    model = StandoutsV2Response.model_validate(payload)

    assert model.status == "active"
    assert model.expiration is not None
    assert len(model.free) == 1
    assert len(model.paid) == 1

    free = model.free[0]
    assert free.subject_id == "standout-1"
    assert free.content is not None
    assert free.content.photo is not None
    assert free.content.photo.content_id == "standout-content-1"
    assert free.content.photo.bounding_box is not None
    # The paid subject omits content -> None.
    assert model.paid[0].content is None

    assert _round_trips(model)


def test_standouts_v2_response_empty():
    model = StandoutsV2Response.model_validate({})
    assert model.status is None
    assert model.expiration is None
    assert model.free == []
    assert model.paid == []
    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# StandoutsV3Response
# --------------------------------------------------------------------------- #


def test_standouts_v3_response_parses():
    payload = load_fixture("standouts_v3_response.json")
    model = StandoutsV3Response.model_validate(payload)

    assert model.status == "active"
    assert model.view_token == "standouts-view-token"
    assert [s.subject_id for s in model.standouts] == [
        "standout-v3-1",
        "standout-v3-2",
    ]
    assert model.standouts[0].content is not None
    assert model.standouts[1].content is None

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# LikesYouResponse
# --------------------------------------------------------------------------- #


def test_likes_you_response_parses():
    payload = load_fixture("likes_you_response.json")
    model = LikesYouResponse.model_validate(payload)

    assert len(model.likes) == 1
    like = model.likes[0]
    assert like.subject_id == "liker-1"
    assert like.show_match_note is True
    assert like.initiated_with == "standard"
    assert like.rating_token == "liker-token-1"

    assert len(model.sorts) == 1
    assert model.sorts[0].id == "recent"

    assert len(model.sorted_likes) == 1
    # The explicit "sortID" alias feeds sort_id.
    assert model.sorted_likes[0].sort_id == "recent"
    assert model.sorted_likes[0].data[0].subject_id == "liker-2"

    assert len(model.hidden_likes) == 1
    assert model.hidden_likes[0].id == "hidden-1"
    assert model.view_token == "likes-view-token"

    assert _round_trips(model)


def test_likes_you_response_empty():
    model = LikesYouResponse.model_validate({})
    assert model.likes == []
    assert model.sorts == []
    assert model.sorted_likes == []
    assert model.hidden_likes == []
    assert model.view_token is None
    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# SelfContentResponse
# --------------------------------------------------------------------------- #


def test_self_content_response_parses():
    payload = load_fixture("self_content_response.json")
    model = SelfContentResponse.model_validate(payload)

    content = model.content
    assert len(content.photos) == 1
    assert content.photos[0].content_id == "self-photo-1"
    assert content.photos[0].selfie_verified is True

    assert len(content.answers) == 1
    answer = content.answers[0]
    assert answer.content_id == "self-answer-1"
    assert answer.transcription_metadata is not None
    assert answer.transcription_metadata.type == "voice"
    assert answer.transcription_metadata.waveform == "AAAABBBB"

    assert content.prompt_poll is not None
    assert content.prompt_poll.options == ["Option A", "Option B"]
    assert content.prompt_poll.selected_option_index == 0
    assert content.video_prompt is not None
    assert content.video_prompt.video_url == "https://cdn.example/self-video.mp4"
    assert content.date_idea is not None
    assert content.date_idea.options == ["Coffee", "Walk in the park"]

    assert _round_trips(model)


# --------------------------------------------------------------------------- #
# LikeLimit
# --------------------------------------------------------------------------- #


def test_like_limit_parses():
    payload = load_fixture("like_limit.json")
    model = LikeLimit.model_validate(payload)

    assert model.likes_left == 8
    # Explicit "superlikesLeft" alias (not the to_camel "superLikesLeft").
    assert model.super_likes_left == 1
    assert model.free_super_likes_left == 0
    assert model.free_super_like_expiration is not None

    dumped = model.model_dump(by_alias=True)
    assert dumped["superlikesLeft"] == 1
    assert "superLikesLeft" not in dumped

    assert _round_trips(model)


def test_like_limit_minimal():
    model = LikeLimit.model_validate({"likesLeft": 3, "superlikesLeft": 0})
    assert model.likes_left == 3
    assert model.super_likes_left == 0
    assert model.free_super_likes_left is None
    assert model.free_super_like_expiration is None
    assert _round_trips(model)
