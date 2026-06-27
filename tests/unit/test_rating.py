"""Offline unit tests for ``client.rating.*``.

Covers ``rate`` (photo path, answer path with prompt-text resolution and
text-review, comment/no-comment, superlike toggle, the ``TypeError`` branch),
``respond``, ``block``, ``limit``, and the private ``_run_text_review`` helper.
All HTTP is mocked with respx — no network, no real data.
"""

import json
from typing import cast

import httpx
import pytest

from hinge.models import (
    AnswerContent,
    PhotoContent,
    Prompt,
    PromptsResponse,
    RecommendationSubject,
)
from hinge.prompts_manager import HingePromptsManager

LIMIT_JSON = {"likesLeft": 7, "superlikesLeft": 3}
RATE_JSON = {"limit": LIMIT_JSON}


def _subject(
    subject_id: str = "subj-1",
    rating_token: str = "tok-abc",
) -> RecommendationSubject:
    return RecommendationSubject(
        subject_id=subject_id,
        rating_token=rating_token,
        origin="discover",
    )


def _photo() -> PhotoContent:
    return PhotoContent(
        cdn_id="cdn-1",
        content_id="photo-1",
        url="https://cdn.example.test/p1.jpg",
    )


def _answer(
    response: str | None = "Tacos, always",
    question_id: str = "q1",
) -> AnswerContent:
    return AnswerContent(
        content_id="answer-1",
        question_id=question_id,
        response=response,
    )


def _last_body(route) -> dict:
    return json.loads(route.calls.last.request.content)


# --------------------------------------------------------------------------- #
# limit()
# --------------------------------------------------------------------------- #


async def test_limit_success(auth_client, base_url, respx_mock):
    route = respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(200, json=LIMIT_JSON),
    )

    limit = await auth_client.rating.limit()

    assert route.called
    assert limit.likes_left == 7
    assert limit.super_likes_left == 3
    # Authenticated client sends a bearer token.
    assert route.calls.last.request.headers["Authorization"] == (
        "Bearer test-hinge-token"
    )


async def test_limit_raises_on_error_status(auth_client, base_url, respx_mock):
    respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.rating.limit()


# --------------------------------------------------------------------------- #
# rate() — PhotoContent path
# --------------------------------------------------------------------------- #


async def test_rate_photo_like_no_comment(auth_client, base_url, respx_mock):
    route = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    result = await auth_client.rating.rate(_subject(), _photo())

    assert result.limit.likes_left == 7
    body = _last_body(route)
    assert body["rating"] == "like"
    assert body["initiatedWith"] == "standard"
    assert body["subjectId"] == "subj-1"
    assert body["ratingToken"] == "tok-abc"
    assert body["sessionId"] == auth_client.session_id
    # No comment -> no text-review run id, no comment key in content.
    assert "hcmRunId" not in body
    assert body["content"]["photo"] == {
        "contentId": "photo-1",
        "url": "https://cdn.example.test/p1.jpg",
        "cdnId": "cdn-1",
    }
    assert "comment" not in body["content"]
    assert "prompt" not in body["content"]


async def test_rate_photo_with_comment_runs_text_review(
    auth_client,
    base_url,
    respx_mock,
):
    review = respx_mock.post(f"{base_url}/flag/textreview").mock(
        return_value=httpx.Response(200, json={"hcmRunId": "run-xyz"}),
    )
    initiate = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    await auth_client.rating.rate(
        _subject(subject_id="subj-9"),
        _photo(),
        comment="Love this shot",
    )

    # Text review fired first with the right payload.
    assert review.called
    review_body = _last_body(review)
    assert review_body == {"text": "Love this shot", "receiverId": "subj-9"}

    body = _last_body(initiate)
    assert body["rating"] == "note"
    assert body["hcmRunId"] == "run-xyz"
    assert body["content"]["comment"] == "Love this shot"
    assert body["content"]["photo"]["contentId"] == "photo-1"


@pytest.mark.parametrize(
    ("use_superlike", "expected"),
    [(False, "standard"), (True, "superlike")],
)
async def test_rate_photo_superlike_toggle(
    auth_client,
    base_url,
    respx_mock,
    use_superlike,
    expected,
):
    route = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    await auth_client.rating.rate(
        _subject(),
        _photo(),
        use_superlike=use_superlike,
    )

    assert _last_body(route)["initiatedWith"] == expected


async def test_rate_photo_raises_on_error_status(auth_client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(400, json={"error": "bad"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.rating.rate(_subject(), _photo())


# --------------------------------------------------------------------------- #
# rate() — AnswerContent path (+ _resolve_prompt_text)
# --------------------------------------------------------------------------- #


async def test_rate_answer_without_prompts_manager(
    auth_client,
    base_url,
    respx_mock,
):
    # No prompt catalogue loaded -> question text resolves to "".
    auth_client.prompts_manager = None
    route = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    await auth_client.rating.rate(_subject(), _answer(response="Tacos, always"))

    prompt = _last_body(route)["content"]["prompt"]
    assert prompt == {
        "answer": "Tacos, always",
        "contentId": "answer-1",
        "question": "",
    }


async def test_rate_answer_resolves_prompt_text(auth_client, base_url, respx_mock):
    auth_client.prompts_manager = HingePromptsManager(
        PromptsResponse(
            prompts=[
                Prompt(
                    id="q1",
                    prompt="My simple pleasures",
                    is_selectable=True,
                    is_new=False,
                ),
            ],
            categories=[],
        ),
    )
    route = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    await auth_client.rating.rate(_subject(), _answer(question_id="q1"))

    assert _last_body(route)["content"]["prompt"]["question"] == "My simple pleasures"


async def test_rate_answer_none_response_falls_back_to_empty(
    auth_client,
    base_url,
    respx_mock,
):
    auth_client.prompts_manager = None
    route = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    await auth_client.rating.rate(_subject(), _answer(response=None))

    assert _last_body(route)["content"]["prompt"]["answer"] == ""


async def test_rate_answer_with_comment(auth_client, base_url, respx_mock):
    auth_client.prompts_manager = None
    review = respx_mock.post(f"{base_url}/flag/textreview").mock(
        return_value=httpx.Response(200, json={"hcmRunId": "run-7"}),
    )
    initiate = respx_mock.post(f"{base_url}/rate/v2/initiate").mock(
        return_value=httpx.Response(200, json=RATE_JSON),
    )

    await auth_client.rating.rate(
        _subject(),
        _answer(),
        comment="Same here!",
    )

    assert review.called
    body = _last_body(initiate)
    assert body["rating"] == "note"
    assert body["hcmRunId"] == "run-7"
    assert body["content"]["comment"] == "Same here!"
    assert "prompt" in body["content"]


async def test_rate_bad_content_item_raises_type_error(auth_client):
    bad = cast(PhotoContent, object())

    with pytest.raises(TypeError, match="PhotoContent or AnswerContent"):
        await auth_client.rating.rate(_subject(), bad)


# --------------------------------------------------------------------------- #
# _run_text_review()
# --------------------------------------------------------------------------- #


async def test_run_text_review_returns_run_id(auth_client, base_url, respx_mock):
    route = respx_mock.post(f"{base_url}/flag/textreview").mock(
        return_value=httpx.Response(200, json={"hcmRunId": "abc-123"}),
    )

    run_id = await auth_client.rating._run_text_review(
        text="hello there",
        receiver_id="rcv-1",
    )

    assert run_id == "abc-123"
    assert _last_body(route) == {"text": "hello there", "receiverId": "rcv-1"}


async def test_run_text_review_raises_on_error_status(
    auth_client,
    base_url,
    respx_mock,
):
    respx_mock.post(f"{base_url}/flag/textreview").mock(
        return_value=httpx.Response(503, json={"error": "down"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.rating._run_text_review(text="x", receiver_id="y")


# --------------------------------------------------------------------------- #
# respond()
# --------------------------------------------------------------------------- #


async def test_respond_like_without_sort_type(auth_client, base_url, respx_mock):
    route = respx_mock.post(f"{base_url}/rate/v2/respond").mock(
        return_value=httpx.Response(200, json={"ok": True}),
    )

    result = await auth_client.rating.respond("subj-2", "like")

    assert result == {"ok": True}
    body = _last_body(route)
    assert body["subjectId"] == "subj-2"
    assert body["rating"] == "like"
    assert body["sessionId"] == auth_client.session_id
    # sort_type is None -> excluded.
    assert "sortType" not in body


async def test_respond_block_with_sort_type(auth_client, base_url, respx_mock):
    route = respx_mock.post(f"{base_url}/rate/v2/respond").mock(
        return_value=httpx.Response(200, json={"ok": True}),
    )

    await auth_client.rating.respond("subj-3", "block", sort_type="recent")

    body = _last_body(route)
    assert body["rating"] == "block"
    assert body["sortType"] == "recent"


async def test_respond_raises_on_error_status(auth_client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/rate/v2/respond").mock(
        return_value=httpx.Response(422, json={"error": "nope"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.rating.respond("subj-4", "like")


# --------------------------------------------------------------------------- #
# block()
# --------------------------------------------------------------------------- #


async def test_block_default(auth_client, base_url, respx_mock):
    route = respx_mock.post(f"{base_url}/rate/v2/match").mock(
        return_value=httpx.Response(200, json={"blocked": True}),
    )

    result = await auth_client.rating.block("subj-5")

    assert result == {"blocked": True}
    body = _last_body(route)
    assert body["subjectId"] == "subj-5"
    assert body["rating"] == "block"
    assert body["secondChanceEligible"] is False
    assert body["sessionId"] == auth_client.session_id


async def test_block_second_chance_eligible(auth_client, base_url, respx_mock):
    route = respx_mock.post(f"{base_url}/rate/v2/match").mock(
        return_value=httpx.Response(200, json={"blocked": True}),
    )

    await auth_client.rating.block("subj-6", second_chance_eligible=True)

    assert _last_body(route)["secondChanceEligible"] is True


async def test_block_raises_on_error_status(auth_client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/rate/v2/match").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.rating.block("subj-7")
