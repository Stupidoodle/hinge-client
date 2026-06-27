"""Unit tests for ``client.content.*`` (ContentResource).

Covers settings/update_settings, evaluate_prompt, fresh_start_eligible
(true/false/missing), fresh_start (success/error), store_account, config,
and boost_status. All HTTP is mocked offline with respx.
"""

import json

import httpx
import pytest

from hinge.models import ContentSettings, PromptEvaluation


# --- settings ---------------------------------------------------------------


async def test_settings_success(auth_client, respx_mock, base_url):
    route = respx_mock.get(f"{base_url}/content/v1/settings").mock(
        return_value=httpx.Response(
            200,
            json={"isSmartPhotoOptIn": True, "isConvoStartersOptIn": False},
        ),
    )

    result = await auth_client.content.settings()

    assert isinstance(result, ContentSettings)
    assert result.is_smart_photo_opt_in is True
    assert result.is_convo_starters_opt_in is False
    # Authenticated requests carry the bearer token.
    auth_header = route.calls.last.request.headers["Authorization"]
    assert auth_header == "Bearer test-hinge-token"


async def test_settings_defaults_when_fields_missing(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/content/v1/settings").mock(
        return_value=httpx.Response(200, json={}),
    )

    result = await auth_client.content.settings()

    assert result.is_smart_photo_opt_in is False
    assert result.is_convo_starters_opt_in is False


async def test_settings_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/content/v1/settings").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.settings()


# --- update_settings --------------------------------------------------------


async def test_update_settings_success_sends_camel_case(
    auth_client, respx_mock, base_url
):
    route = respx_mock.patch(f"{base_url}/content/v1/settings").mock(
        return_value=httpx.Response(
            200,
            json={"isSmartPhotoOptIn": True, "isConvoStartersOptIn": True},
        ),
    )

    payload = ContentSettings(
        is_smart_photo_opt_in=True,
        is_convo_starters_opt_in=True,
    )
    result = await auth_client.content.update_settings(payload)

    assert isinstance(result, ContentSettings)
    assert result.is_smart_photo_opt_in is True
    assert result.is_convo_starters_opt_in is True

    sent = json.loads(route.calls.last.request.content)
    assert sent == {"isSmartPhotoOptIn": True, "isConvoStartersOptIn": True}


async def test_update_settings_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.patch(f"{base_url}/content/v1/settings").mock(
        return_value=httpx.Response(400, json={"error": "bad"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.update_settings(ContentSettings())


# --- evaluate_prompt --------------------------------------------------------


async def test_evaluate_prompt_success(auth_client, respx_mock, base_url):
    route = respx_mock.post(f"{base_url}/content/v1/answer/evaluate").mock(
        return_value=httpx.Response(
            200,
            json={
                "evaluation": "great",
                "detail": "nice and specific",
                "feedbackToken": "tok-123",
            },
        ),
    )

    result = await auth_client.content.evaluate_prompt("prompt-42", "my answer")

    assert isinstance(result, PromptEvaluation)
    assert result.evaluation == "great"
    assert result.detail == "nice and specific"
    assert result.feedback_token == "tok-123"

    sent = json.loads(route.calls.last.request.content)
    assert sent == {"promptId": "prompt-42", "answer": "my answer"}


async def test_evaluate_prompt_empty_body_defaults_none(
    auth_client, respx_mock, base_url
):
    respx_mock.post(f"{base_url}/content/v1/answer/evaluate").mock(
        return_value=httpx.Response(200, json={}),
    )

    result = await auth_client.content.evaluate_prompt("p", "a")

    assert result.evaluation is None
    assert result.detail is None
    assert result.feedback_token is None


async def test_evaluate_prompt_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.post(f"{base_url}/content/v1/answer/evaluate").mock(
        return_value=httpx.Response(422, json={"error": "invalid"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.evaluate_prompt("p", "a")


# --- fresh_start_eligible ---------------------------------------------------


async def test_fresh_start_eligible_true(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/freshstart/eligible").mock(
        return_value=httpx.Response(200, json={"eligible": True}),
    )

    assert await auth_client.content.fresh_start_eligible() is True


async def test_fresh_start_eligible_false(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/freshstart/eligible").mock(
        return_value=httpx.Response(200, json={"eligible": False}),
    )

    assert await auth_client.content.fresh_start_eligible() is False


async def test_fresh_start_eligible_missing_key_defaults_false(
    auth_client, respx_mock, base_url
):
    respx_mock.get(f"{base_url}/freshstart/eligible").mock(
        return_value=httpx.Response(200, json={}),
    )

    assert await auth_client.content.fresh_start_eligible() is False


async def test_fresh_start_eligible_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/freshstart/eligible").mock(
        return_value=httpx.Response(503, json={"error": "down"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.fresh_start_eligible()


# --- fresh_start ------------------------------------------------------------


async def test_fresh_start_success_returns_true(auth_client, respx_mock, base_url):
    route = respx_mock.post(f"{base_url}/freshstart").mock(
        return_value=httpx.Response(200, json={}),
    )

    assert await auth_client.content.fresh_start() is True
    assert route.called


async def test_fresh_start_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.post(f"{base_url}/freshstart").mock(
        return_value=httpx.Response(409, json={"error": "not eligible"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.fresh_start()


# --- store_account ----------------------------------------------------------


async def test_store_account_success(auth_client, respx_mock, base_url):
    body = {"premium": True, "subscriptions": [{"id": "sub-1"}]}
    respx_mock.get(f"{base_url}/store/v2/account").mock(
        return_value=httpx.Response(200, json=body),
    )

    result = await auth_client.content.store_account()

    assert result == body


async def test_store_account_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/store/v2/account").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.store_account()


# --- config -----------------------------------------------------------------


async def test_config_success(auth_client, respx_mock, base_url):
    body = {"genders": ["man", "woman"], "version": 3}
    respx_mock.get(f"{base_url}/config/v3").mock(
        return_value=httpx.Response(200, json=body),
    )

    result = await auth_client.content.config()

    assert result == body


async def test_config_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/config/v3").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.config()


# --- boost_status -----------------------------------------------------------


async def test_boost_status_success(auth_client, respx_mock, base_url):
    body = {"active": False, "remaining": 0}
    respx_mock.get(f"{base_url}/boost/status").mock(
        return_value=httpx.Response(200, json=body),
    )

    result = await auth_client.content.boost_status()

    assert result == body


async def test_boost_status_raises_on_error(auth_client, respx_mock, base_url):
    respx_mock.get(f"{base_url}/boost/status").mock(
        return_value=httpx.Response(404, json={"error": "missing"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.content.boost_status()
