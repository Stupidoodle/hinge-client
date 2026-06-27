"""Unit tests for ``client.recommendations.*`` (RecommendationsResource).

Covers list (cache population, dual id keys, feed-exhausted branch, save,
already-cached no-op, validation error), repeat, likes_received (with/without
sort), matches, standouts, standouts_v3 (fresh fetch with/without ETag, 304
cache hit), and remove (present/absent). All HTTP is mocked offline with respx.
"""

import json

import httpx
import pytest
from pydantic import ValidationError

from hinge.models import (
    LikesYouResponse,
    RecommendationsResponse,
    RecommendationSubject,
    StandoutsV2Response,
    StandoutsV3Response,
)


# --- list -------------------------------------------------------------------


async def test_list_populates_cache_and_saves(
    auth_client, respx_mock, base_url, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    recs_json = {
        "feeds": [
            {
                "origin": "compatibles",
                "subjects": [
                    {"subjectId": "subj-a", "ratingToken": "tok-a"},
                ],
            },
            {
                # Second feed uses snake_case keys to exercise the
                # ``subject_data.get("subject_id")`` fallback branch.
                "origin": "nearby",
                "subjects": [
                    {"subject_id": "subj-b", "rating_token": "tok-b"},
                ],
            },
        ],
    }
    route = respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(200, json=recs_json),
    )

    result = await auth_client.recommendations.list()

    assert isinstance(result, RecommendationsResponse)
    assert len(result.feeds) == 2
    # Both subjects cached, each tagged with its feed origin.
    assert set(auth_client._rec_cache) == {"subj-a", "subj-b"}
    assert auth_client._rec_cache["subj-a"].origin == "compatibles"
    assert auth_client._rec_cache["subj-b"].origin == "nearby"
    assert auth_client.feed_exhausted is False
    # Recommendations persisted to the session-scoped file (in cwd).
    saved = tmp_path / f"recommendations_{auth_client.session_id}.json"
    assert saved.exists()
    # Request body carries the player id + flags.
    sent = route.calls.last.request
    body = json.loads(sent.content)
    assert body == {
        "playerId": "test-identity-id",
        "newHere": False,
        "activeToday": False,
    }


async def test_list_marks_feed_exhausted_when_empty(
    auth_client, respx_mock, base_url, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    recs_json = {"feeds": [{"origin": "compatibles", "subjects": []}]}
    respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(200, json=recs_json),
    )

    result = await auth_client.recommendations.list()

    assert auth_client.feed_exhausted is True
    assert auth_client._rec_cache == {}
    assert result.feeds[0].subjects == []


async def test_list_skips_subjects_already_cached(
    auth_client, respx_mock, base_url, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    recs_json = {
        "feeds": [
            {
                "origin": "compatibles",
                "subjects": [{"subjectId": "subj-a", "ratingToken": "tok-a"}],
            },
        ],
    }
    respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(200, json=recs_json),
    )

    await auth_client.recommendations.list()
    first = auth_client._rec_cache["subj-a"]
    # Second fetch with the same subject: already cached -> not re-added.
    await auth_client.recommendations.list()

    assert auth_client._rec_cache["subj-a"] is first
    assert len(auth_client._rec_cache) == 1


async def test_list_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.recommendations.list()


async def test_list_raises_on_invalid_subject(
    auth_client, respx_mock, base_url, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    # Subject missing the required ``ratingToken`` -> ValidationError inside
    # the per-subject ``model_validate`` call.
    recs_json = {
        "feeds": [
            {"origin": "compatibles", "subjects": [{"subjectId": "subj-a"}]},
        ],
    }
    respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(200, json=recs_json),
    )

    with pytest.raises(ValidationError):
        await auth_client.recommendations.list()


async def test_list_without_feeds_key(
    auth_client, respx_mock, base_url, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    # No "feeds" key: the cache-population guard is skipped, then the required
    # feeds field fails model validation.
    respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(200, json={}),
    )

    with pytest.raises(ValidationError):
        await auth_client.recommendations.list()

    assert auth_client._rec_cache == {}
    assert auth_client.feed_exhausted is True


async def test_list_feed_without_subjects_key(
    auth_client, respx_mock, base_url, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    # A feed missing "subjects": the per-feed guard skips it, then the required
    # subjects field fails model validation.
    respx_mock.post(f"{base_url}/rec/v2").mock(
        return_value=httpx.Response(200, json={"feeds": [{"origin": "compatibles"}]}),
    )

    with pytest.raises(ValidationError):
        await auth_client.recommendations.list()

    assert auth_client._rec_cache == {}
    assert auth_client.feed_exhausted is True


# --- repeat -----------------------------------------------------------------


async def test_repeat_resets_exhausted_flag(auth_client, respx_mock, base_url):
    auth_client.feed_exhausted = True
    route = respx_mock.get(f"{base_url}/user/repeat").mock(
        return_value=httpx.Response(200, json={"status": "ok"}),
    )

    result = await auth_client.recommendations.repeat()

    assert result == {"status": "ok"}
    assert auth_client.feed_exhausted is False
    assert route.called


async def test_repeat_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/user/repeat").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.recommendations.repeat()


# --- likes_received ---------------------------------------------------------


async def test_likes_received_no_sort_omits_params(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/like/v2").mock(
        return_value=httpx.Response(
            200,
            json={"likes": [{"subjectId": "subj-a"}], "viewToken": "vt-1"},
        ),
    )

    result = await auth_client.recommendations.likes_received()

    assert isinstance(result, LikesYouResponse)
    assert result.view_token == "vt-1"
    assert result.likes[0].subject_id == "subj-a"
    # No sort -> no query string.
    assert route.calls.last.request.url.query == b""


async def test_likes_received_with_sort_sends_param(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/like/v2").mock(
        return_value=httpx.Response(200, json={}),
    )

    result = await auth_client.recommendations.likes_received(sort="recent")

    assert isinstance(result, LikesYouResponse)
    assert result.likes == []
    assert b"sort=recent" in route.calls.last.request.url.query


async def test_likes_received_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/like/v2").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.recommendations.likes_received()


# --- matches ----------------------------------------------------------------


async def test_matches_returns_raw_json(auth_client, respx_mock, base_url):
    payload = {"connections": [{"id": "c1"}]}
    respx_mock.get(f"{base_url}/connection/v2").mock(
        return_value=httpx.Response(200, json=payload),
    )

    result = await auth_client.recommendations.matches()

    assert result == payload


async def test_matches_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/connection/v2").mock(
        return_value=httpx.Response(403, json={"error": "forbidden"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.recommendations.matches()


# --- standouts (v2) ---------------------------------------------------------


async def test_standouts_success(auth_client, respx_mock, base_url):
    payload = {
        "status": "ok",
        "free": [{"subjectId": "s1", "ratingToken": "t1"}],
        "paid": [],
    }
    respx_mock.get(f"{base_url}/standouts/v2").mock(
        return_value=httpx.Response(200, json=payload),
    )

    result = await auth_client.recommendations.standouts()

    assert isinstance(result, StandoutsV2Response)
    assert result.status == "ok"
    assert result.free[0].subject_id == "s1"
    assert result.paid == []


async def test_standouts_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/standouts/v2").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.recommendations.standouts()


# --- standouts_v3 (ETag caching) --------------------------------------------


async def test_standouts_v3_fresh_fetch_stores_etag(auth_client, respx_mock, base_url):
    payload = {
        "status": "ok",
        "standouts": [{"subjectId": "s1", "ratingToken": "t1"}],
        "viewToken": "vt-1",
    }
    route = respx_mock.get(f"{base_url}/standouts/v3").mock(
        return_value=httpx.Response(200, json=payload, headers={"ETag": "etag-1"}),
    )

    result = await auth_client.recommendations.standouts_v3()

    assert isinstance(result, StandoutsV3Response)
    assert result.view_token == "vt-1"
    assert auth_client._standouts_etag == "etag-1"
    assert auth_client._standouts_cache is result
    # No prior etag -> no conditional header on the request.
    assert "If-None-Match" not in route.calls.last.request.headers


async def test_standouts_v3_fresh_fetch_without_etag_header(
    auth_client, respx_mock, base_url
):
    payload = {"status": "ok", "standouts": []}
    respx_mock.get(f"{base_url}/standouts/v3").mock(
        return_value=httpx.Response(200, json=payload),
    )

    result = await auth_client.recommendations.standouts_v3()

    assert isinstance(result, StandoutsV3Response)
    # Server returned no ETag -> nothing cached for conditional requests.
    assert auth_client._standouts_etag is None
    assert auth_client._standouts_cache is result


async def test_standouts_v3_not_modified_returns_cached(
    auth_client, respx_mock, base_url
):
    cached = StandoutsV3Response(status="cached", standouts=[])
    auth_client._standouts_etag = "etag-existing"
    auth_client._standouts_cache = cached
    route = respx_mock.get(f"{base_url}/standouts/v3").mock(
        return_value=httpx.Response(304),
    )

    result = await auth_client.recommendations.standouts_v3()

    assert result is cached
    # Existing etag is sent as the conditional header.
    assert route.calls.last.request.headers["If-None-Match"] == "etag-existing"


async def test_standouts_v3_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/standouts/v3").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.recommendations.standouts_v3()


# --- remove -----------------------------------------------------------------


async def test_remove_deletes_and_saves(auth_client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    auth_client._rec_cache = {
        "subj-a": RecommendationSubject(subject_id="subj-a", rating_token="tok-a"),
    }

    auth_client.recommendations.remove("subj-a")

    assert "subj-a" not in auth_client._rec_cache
    # Save was triggered, writing the (now empty) cache file.
    saved = tmp_path / f"recommendations_{auth_client.session_id}.json"
    assert saved.exists()


async def test_remove_missing_subject_is_noop(auth_client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    auth_client._rec_cache = {
        "subj-a": RecommendationSubject(subject_id="subj-a", rating_token="tok-a"),
    }

    auth_client.recommendations.remove("does-not-exist")

    # Cache untouched and no save performed (no file written).
    assert set(auth_client._rec_cache) == {"subj-a"}
    saved = tmp_path / f"recommendations_{auth_client.session_id}.json"
    assert not saved.exists()
