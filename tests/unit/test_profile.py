"""Offline unit tests for ``client.profile.*`` resource methods.

Every Hinge HTTP call is mocked with respx; we assert the request method,
URL/query, and JSON payload, plus the parsed return type and field values.
Both success and error (non-2xx → ``raise_for_status``) branches are covered.
"""

import json

import httpx
import pytest

from hinge.models import (
    AnswerContentPayload,
    Preferences,
    ProfileContent,
    SelfContentResponse,
    SelfProfileResponse,
    TextAnswer,
    UserProfile,
    UserProfileV2,
)

# --- Synthetic payload builders --------------------------------------------


def _self_profile_json() -> dict:
    return {
        "userId": "self-123",
        "created": "2024-01-01T00:00:00Z",
        "registered": "2024-01-02T00:00:00Z",
        "modified": "2024-01-03T00:00:00Z",
        "lastActiveOptIn": True,
        "paused": False,
        "profile": {
            "firstName": "Alex",
            "age": 30,
            "location": {"name": "Paris"},
        },
    }


def _content_content_json() -> dict:
    return {
        "photos": [
            {"cdnId": "cdn1", "contentId": "c1", "url": "https://img/1.jpg"},
        ],
        "answers": [
            {"contentId": "a1", "questionId": "q1", "response": "hi"},
        ],
    }


def _self_content_json() -> dict:
    return {"content": _content_content_json()}


def _preferences_json() -> dict:
    return {
        "genderedAgeRanges": {"1": {"min": 25, "max": 35}},
        "dealbreakers": {
            "marijuana": False,
            "smoking": False,
            "maxDistance": False,
            "drinking": False,
            "educationAttained": False,
            "genderedHeight": {},
            "politics": False,
            "relationshipTypes": False,
            "drugs": False,
            "datingIntentions": False,
            "familyPlans": False,
            "genderedAge": {},
            "religions": False,
            "ethnicities": False,
            "children": False,
        },
        "religions": [],
        "drinking": [],
        "genderedHeightRanges": {},
        "marijuana": [],
        "relationshipTypes": [],
        "drugs": [],
        "maxDistance": 50,
        "children": [],
        "ethnicities": [],
        "smoking": [],
        "educationAttained": [],
        "familyPlans": [],
        "datingIntentions": [],
        "politics": [],
        "genderPreferences": [1],
    }


def _public_profile_json(user_id: str, name: str) -> dict:
    return {
        "userId": user_id,
        "profile": {"firstName": name, "location": {"name": "Paris"}},
    }


def _public_profile_v2_json(identity_id: str, name: str) -> dict:
    return {
        "identityId": identity_id,
        "profile": {"firstName": name, "location": {"name": "NYC"}},
    }


def _profile_content_json(user_id: str) -> dict:
    return {"userId": user_id, "content": _content_content_json()}


def _sent_json(route) -> object:
    return json.loads(route.calls.last.request.content)


# --- me() ------------------------------------------------------------------


async def test_me_success(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/user/v3").mock(
        return_value=httpx.Response(200, json=_self_profile_json()),
    )
    result = await auth_client.profile.me()

    assert isinstance(result, SelfProfileResponse)
    assert result.user_id == "self-123"
    assert result.paused is False
    assert result.profile.first_name == "Alex"
    req = route.calls.last.request
    assert req.method == "GET"
    assert req.url.path == "/user/v3"
    assert req.headers["Authorization"] == "Bearer test-hinge-token"


async def test_me_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/user/v3").mock(
        return_value=httpx.Response(500, text="boom"),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.me()


# --- my_content() ----------------------------------------------------------


async def test_my_content_success(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/content/v2").mock(
        return_value=httpx.Response(200, json=_self_content_json()),
    )
    result = await auth_client.profile.my_content()

    assert isinstance(result, SelfContentResponse)
    assert result.content.photos[0].cdn_id == "cdn1"
    assert result.content.answers[0].question_id == "q1"
    assert route.calls.last.request.method == "GET"


async def test_my_content_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/content/v2").mock(
        return_value=httpx.Response(404),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.my_content()


# --- state() ---------------------------------------------------------------


async def test_state_success(auth_client, respx_mock, base_url):
    payload = {"complete": True, "missing": []}
    route = respx_mock.get(f"{base_url}/profilestate/profile").mock(
        return_value=httpx.Response(200, json=payload),
    )
    result = await auth_client.profile.state()

    assert result == payload
    assert route.calls.last.request.method == "GET"
    assert route.calls.last.request.url.path == "/profilestate/profile"


async def test_state_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/profilestate/profile").mock(
        return_value=httpx.Response(503),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.state()


# --- basics_missing() ------------------------------------------------------


async def test_basics_missing_success(auth_client, respx_mock, base_url):
    payload = {"missing": ["height", "job"]}
    route = respx_mock.get(f"{base_url}/profilestate/basics/missing").mock(
        return_value=httpx.Response(200, json=payload),
    )
    result = await auth_client.profile.basics_missing()

    assert result == payload
    assert route.calls.last.request.url.path == "/profilestate/basics/missing"


async def test_basics_missing_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/profilestate/basics/missing").mock(
        return_value=httpx.Response(500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.basics_missing()


# --- preferences() ---------------------------------------------------------


async def test_preferences_success(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/preference/v2/selected").mock(
        return_value=httpx.Response(200, json=_preferences_json()),
    )
    result = await auth_client.profile.preferences()

    assert isinstance(result, Preferences)
    assert result.max_distance == 50
    assert result.gender_preferences == [1]
    assert result.gendered_age_ranges.women.min == 25
    assert route.calls.last.request.method == "GET"


async def test_preferences_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/preference/v2/selected").mock(
        return_value=httpx.Response(401),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.preferences()


# --- update_preferences() --------------------------------------------------


async def test_update_preferences_success(auth_client, respx_mock, base_url):
    prefs = Preferences.model_validate(_preferences_json())
    route = respx_mock.patch(f"{base_url}/preference/v2/selected").mock(
        return_value=httpx.Response(200, json={"ok": True}),
    )
    result = await auth_client.profile.update_preferences(prefs)

    assert result == {"ok": True}
    req = route.calls.last.request
    assert req.method == "PATCH"
    sent = _sent_json(route)
    assert isinstance(sent, list)
    assert len(sent) == 1
    assert sent[0]["genderPreferences"] == [1]
    assert "dealbreakers" in sent[0]
    # exclude_none drops the empty gendered-height range entirely.
    assert sent[0]["genderedHeightRanges"] == {}


async def test_update_preferences_error_raises(auth_client, respx_mock, base_url):
    prefs = Preferences.model_validate(_preferences_json())
    respx_mock.patch(f"{base_url}/preference/v2/selected").mock(
        return_value=httpx.Response(422),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.update_preferences(prefs)


# --- update() --------------------------------------------------------------


async def test_update_success(auth_client, respx_mock, base_url):
    route = respx_mock.patch(f"{base_url}/user/v2").mock(
        return_value=httpx.Response(200, json={"updated": True}),
    )
    result = await auth_client.profile.update({"firstName": "NewName"})

    assert result == {"updated": True}
    req = route.calls.last.request
    assert req.method == "PATCH"
    assert req.url.path == "/user/v2"
    assert _sent_json(route) == [{"profile": {"firstName": "NewName"}}]


async def test_update_error_raises(auth_client, respx_mock, base_url):
    respx_mock.patch(f"{base_url}/user/v2").mock(
        return_value=httpx.Response(400),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.update({"firstName": "X"})


# --- update_answers() ------------------------------------------------------


async def test_update_answers_success(auth_client, respx_mock, base_url):
    answers = [
        AnswerContentPayload(
            position=0,
            question_id="q1",
            text_answer=TextAnswer(response="hello", question_id="q1"),
        ),
    ]
    route = respx_mock.put(f"{base_url}/content/v1/answers").mock(
        return_value=httpx.Response(200, json={"saved": 1}),
    )
    result = await auth_client.profile.update_answers(answers)

    assert result == {"saved": 1}
    req = route.calls.last.request
    assert req.method == "PUT"
    assert req.url.path == "/content/v1/answers"
    sent = _sent_json(route)
    assert sent == [
        {
            "position": 0,
            "questionId": "q1",
            "textAnswer": {"response": "hello", "questionId": "q1"},
        },
    ]


async def test_update_answers_empty_list(auth_client, respx_mock, base_url):
    route = respx_mock.put(f"{base_url}/content/v1/answers").mock(
        return_value=httpx.Response(200, json={"saved": 0}),
    )
    result = await auth_client.profile.update_answers([])

    assert result == {"saved": 0}
    assert _sent_json(route) == []


async def test_update_answers_error_raises(auth_client, respx_mock, base_url):
    respx_mock.put(f"{base_url}/content/v1/answers").mock(
        return_value=httpx.Response(500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.update_answers([])


# --- put_photos() ----------------------------------------------------------


async def test_put_photos_success(auth_client, respx_mock, base_url):
    photos = [{"cdnId": "abc", "position": 0}, {"cdnId": "def", "position": 1}]
    route = respx_mock.put(f"{base_url}/content/v1/photos").mock(
        return_value=httpx.Response(200, json={"count": 2}),
    )
    result = await auth_client.profile.put_photos(photos)

    assert result == {"count": 2}
    req = route.calls.last.request
    assert req.method == "PUT"
    assert req.url.path == "/content/v1/photos"
    assert _sent_json(route) == {"photos": photos}


async def test_put_photos_error_raises(auth_client, respx_mock, base_url):
    respx_mock.put(f"{base_url}/content/v1/photos").mock(
        return_value=httpx.Response(409),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.put_photos([])


# --- cdn_token() -----------------------------------------------------------


async def test_cdn_token_defaults(auth_client, respx_mock, base_url):
    route = respx_mock.post(f"{base_url}/cdn/token").mock(
        return_value=httpx.Response(200, json={"token": "t"}),
    )
    result = await auth_client.profile.cdn_token()

    assert result == {"token": "t"}
    req = route.calls.last.request
    assert req.method == "POST"
    assert req.url.path == "/cdn/token"
    assert _sent_json(route) == {
        "params": {"tags": "", "phash": "true", "folder": ""},
    }


async def test_cdn_token_explicit_args(auth_client, respx_mock, base_url):
    route = respx_mock.post(f"{base_url}/cdn/token").mock(
        return_value=httpx.Response(200, json={"token": "t"}),
    )
    await auth_client.profile.cdn_token(tags="photo", folder="me")

    assert _sent_json(route) == {
        "params": {"tags": "photo", "phash": "true", "folder": "me"},
    }


async def test_cdn_token_error_raises(auth_client, respx_mock, base_url):
    respx_mock.post(f"{base_url}/cdn/token").mock(
        return_value=httpx.Response(403),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.cdn_token()


# --- get() -----------------------------------------------------------------


async def test_get_success(auth_client, respx_mock, base_url):
    body = [
        _public_profile_json("u1", "Bo"),
        _public_profile_json("u2", "Cleo"),
    ]
    route = respx_mock.get(f"{base_url}/user/v3/public").mock(
        return_value=httpx.Response(200, json=body),
    )
    result = await auth_client.profile.get(["u1", "u2"])

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(p, UserProfile) for p in result)
    assert result[0].user_id == "u1"
    assert result[1].profile.first_name == "Cleo"
    req = route.calls.last.request
    assert req.method == "GET"
    assert req.url.path == "/user/v3/public"
    assert req.url.params["ids"] == "u1,u2"


async def test_get_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/user/v3/public").mock(
        return_value=httpx.Response(500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.get(["u1"])


# --- get_v2() --------------------------------------------------------------


async def test_get_v2_success(auth_client, respx_mock, base_url):
    body = [_public_profile_v2_json("u9", "Dana")]
    route = respx_mock.get(f"{base_url}/user/v2/public").mock(
        return_value=httpx.Response(200, json=body),
    )
    result = await auth_client.profile.get_v2(["u9"])

    assert len(result) == 1
    assert isinstance(result[0], UserProfileV2)
    assert result[0].identity_id == "u9"
    assert result[0].profile.first_name == "Dana"
    req = route.calls.last.request
    assert req.url.path == "/user/v2/public"
    assert req.url.params["ids"] == "u9"


async def test_get_v2_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/user/v2/public").mock(
        return_value=httpx.Response(404),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.get_v2(["u9"])


# --- content() -------------------------------------------------------------


async def test_content_success(auth_client, respx_mock, base_url):
    body = [_profile_content_json("u1"), _profile_content_json("u2")]
    route = respx_mock.get(f"{base_url}/content/v2/public").mock(
        return_value=httpx.Response(200, json=body),
    )
    result = await auth_client.profile.content(["u1", "u2"])

    assert len(result) == 2
    assert all(isinstance(c, ProfileContent) for c in result)
    assert result[0].user_id == "u1"
    assert result[0].content.photos[0].cdn_id == "cdn1"
    req = route.calls.last.request
    assert req.url.path == "/content/v2/public"
    assert req.url.params["ids"] == "u1,u2"


async def test_content_empty_returns_empty_list(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/content/v2/public").mock(
        return_value=httpx.Response(200, json=[]),
    )
    result = await auth_client.profile.content(["u1"])

    assert result == []
    assert route.calls.call_count == 1


async def test_content_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/content/v2/public").mock(
        return_value=httpx.Response(500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.content(["u1"])


# --- traits() --------------------------------------------------------------


async def test_traits_success(auth_client, respx_mock, base_url):
    payload = {"traits": [{"id": "t1", "label": "Adventurous"}]}
    route = respx_mock.get(f"{base_url}/user/v2/traits").mock(
        return_value=httpx.Response(200, json=payload),
    )
    result = await auth_client.profile.traits()

    assert result == payload
    req = route.calls.last.request
    assert req.method == "GET"
    assert req.url.path == "/user/v2/traits"


async def test_traits_error_raises(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/user/v2/traits").mock(
        return_value=httpx.Response(500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.profile.traits()
