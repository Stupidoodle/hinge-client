"""Unit tests for ``client.chat.*`` (the Sendbird/Hinge chat resource).

Covers ``conversations``, ``messages``, ``mark_read``, ``unread_count``,
``send``, ``react`` and the ``_sendbird_headers`` helper. Every HTTP call is
mocked with respx — no network, no real credentials.
"""

import json
import uuid

import httpx
import pytest

from hinge.client import SENDBIRD_APP_ID

SENDBIRD_REST_BASE = f"https://api-{SENDBIRD_APP_ID.lower()}.sendbird.com"


def _body(request: httpx.Request) -> dict:
    """Decode a captured request's JSON body."""
    return json.loads(request.content)


# --------------------------------------------------------------------------- #
# _sendbird_headers
# --------------------------------------------------------------------------- #


def test_sendbird_headers_shape(auth_client):
    headers = auth_client._sendbird_headers()
    assert headers == {
        "Session-Key": "test-sendbird-session-key",
        "Content-Type": "application/json",
    }


def test_sendbird_headers_uses_current_session_key(auth_client):
    auth_client.sendbird_session_key = "rotated-key"
    assert auth_client._sendbird_headers()["Session-Key"] == "rotated-key"


# --------------------------------------------------------------------------- #
# conversations
# --------------------------------------------------------------------------- #


async def test_conversations_success(auth_client, respx_mock):
    url = f"{SENDBIRD_REST_BASE}/v3/users/{auth_client.identity_id}/my_group_channels"
    payload = {"channels": [{"channel_url": "ch-1"}], "next": ""}
    route = respx_mock.get(url).mock(return_value=httpx.Response(200, json=payload))

    result = await auth_client.chat.conversations()

    assert result == payload
    req = route.calls.last.request
    params = req.url.params
    assert params["show_member"] == "true"
    assert params["show_read_receipt"] == "true"
    assert params["show_delivery_receipt"] == "true"
    assert params["show_metadata"] == "true"
    assert params["limit"] == "100"
    assert params["order"] == "latest_last_message"
    assert req.headers["Session-Key"] == "test-sendbird-session-key"


async def test_conversations_custom_limit(auth_client, respx_mock):
    url = f"{SENDBIRD_REST_BASE}/v3/users/{auth_client.identity_id}/my_group_channels"
    route = respx_mock.get(url).mock(
        return_value=httpx.Response(200, json={"channels": []}),
    )

    result = await auth_client.chat.conversations(limit=5)

    assert result == {"channels": []}
    assert route.calls.last.request.url.params["limit"] == "5"


async def test_conversations_error_raises(auth_client, respx_mock):
    url = f"{SENDBIRD_REST_BASE}/v3/users/{auth_client.identity_id}/my_group_channels"
    respx_mock.get(url).mock(return_value=httpx.Response(401, json={"code": 400401}))

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.chat.conversations()


# --------------------------------------------------------------------------- #
# messages
# --------------------------------------------------------------------------- #


async def test_messages_success_defaults(auth_client, respx_mock):
    channel = "sendbird_group_channel_42"
    url = f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}/messages"
    payload = {"messages": [{"message_id": 1, "message": "hi"}]}
    route = respx_mock.get(url).mock(return_value=httpx.Response(200, json=payload))

    result = await auth_client.chat.messages(channel)

    assert result == payload
    params = route.calls.last.request.url.params
    assert params["message_ts"] == "0"
    assert params["prev_limit"] == "0"
    assert params["next_limit"] == "30"
    assert params["include"] == "true"
    assert params["with_sorted_meta_array"] == "true"


async def test_messages_custom_params(auth_client, respx_mock):
    channel = "ch-x"
    url = f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}/messages"
    route = respx_mock.get(url).mock(
        return_value=httpx.Response(200, json={"messages": []}),
    )

    result = await auth_client.chat.messages(
        channel,
        next_limit=10,
        message_ts=1700000000000,
        prev_limit=7,
    )

    assert result == {"messages": []}
    params = route.calls.last.request.url.params
    assert params["next_limit"] == "10"
    assert params["message_ts"] == "1700000000000"
    assert params["prev_limit"] == "7"
    assert route.calls.last.request.headers["Session-Key"] == (
        "test-sendbird-session-key"
    )


async def test_messages_error_raises(auth_client, respx_mock):
    channel = "ch-broken"
    url = f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}/messages"
    respx_mock.get(url).mock(return_value=httpx.Response(500, text="boom"))

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.chat.messages(channel)


# --------------------------------------------------------------------------- #
# mark_read
# --------------------------------------------------------------------------- #


async def test_mark_read_success(auth_client, respx_mock):
    channel = "ch-read"
    url = f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}/messages/mark_as_read"
    route = respx_mock.put(url).mock(return_value=httpx.Response(200, json={}))

    result = await auth_client.chat.mark_read(channel)

    assert result == {}
    req = route.calls.last.request
    assert _body(req) == {"user_id": auth_client.identity_id}
    assert req.headers["Session-Key"] == "test-sendbird-session-key"


async def test_mark_read_error_raises(auth_client, respx_mock):
    channel = "ch-read"
    url = f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}/messages/mark_as_read"
    respx_mock.put(url).mock(return_value=httpx.Response(403, json={"code": 403}))

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.chat.mark_read(channel)


# --------------------------------------------------------------------------- #
# unread_count
# --------------------------------------------------------------------------- #


async def test_unread_count_success(auth_client, respx_mock):
    url = (
        f"{SENDBIRD_REST_BASE}/v3/users/{auth_client.identity_id}/unread_channel_count"
    )
    route = respx_mock.get(url).mock(
        return_value=httpx.Response(200, json={"unread_count": 3}),
    )

    result = await auth_client.chat.unread_count()

    assert result == {"unread_count": 3}
    assert route.calls.last.request.headers["Session-Key"] == (
        "test-sendbird-session-key"
    )


async def test_unread_count_error_raises(auth_client, respx_mock):
    url = (
        f"{SENDBIRD_REST_BASE}/v3/users/{auth_client.identity_id}/unread_channel_count"
    )
    respx_mock.get(url).mock(return_value=httpx.Response(503, text="down"))

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.chat.unread_count()


# --------------------------------------------------------------------------- #
# send
# --------------------------------------------------------------------------- #


async def test_send_success_defaults(auth_client, base_url, respx_mock):
    url = f"{base_url}/message/send"
    route = respx_mock.post(url).mock(
        return_value=httpx.Response(200, json={"messageId": "m1"}),
    )

    result = await auth_client.chat.send("subj-1", "hello there")

    assert result == {"messageId": "m1"}
    req = route.calls.last.request
    body = _body(req)
    assert body["subjectId"] == "subj-1"
    assert body["matchMessage"] is False
    assert body["origin"] == "chat"
    assert body["ays"] is False
    assert body["messageData"] == {
        "message": "hello there",
        "fileUrl": None,
        "fileMetadata": None,
    }
    # dedupId auto-generated as a valid UUID
    uuid.UUID(body["dedupId"])
    # send uses the Hinge default headers (bearer auth), not Sendbird ones
    assert req.headers["Authorization"] == "Bearer test-hinge-token"
    assert "Session-Key" not in req.headers


async def test_send_custom_dedup_and_match_message(auth_client, base_url, respx_mock):
    url = f"{base_url}/message/send"
    route = respx_mock.post(url).mock(
        return_value=httpx.Response(200, json={"ok": True}),
    )

    result = await auth_client.chat.send(
        "subj-2",
        "first message",
        match_message=True,
        dedup_id="fixed-dedup-id",
    )

    assert result == {"ok": True}
    body = _body(route.calls.last.request)
    assert body["dedupId"] == "fixed-dedup-id"
    assert body["matchMessage"] is True


async def test_send_generates_unique_dedup_ids(auth_client, base_url, respx_mock):
    url = f"{base_url}/message/send"
    route = respx_mock.post(url).mock(
        return_value=httpx.Response(200, json={"ok": True}),
    )

    await auth_client.chat.send("s", "a")
    await auth_client.chat.send("s", "b")

    first = _body(route.calls[0].request)["dedupId"]
    second = _body(route.calls[1].request)["dedupId"]
    assert first != second


async def test_send_error_raises(auth_client, base_url, respx_mock):
    url = f"{base_url}/message/send"
    respx_mock.post(url).mock(
        return_value=httpx.Response(400, json={"error": "harassment"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.chat.send("subj", "bad text")


# --------------------------------------------------------------------------- #
# react
# --------------------------------------------------------------------------- #


async def test_react_success_default_reaction(auth_client, respx_mock):
    channel = "ch-react"
    message_id = 99
    url = (
        f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}"
        f"/messages/{message_id}/sorted_metaarray"
    )
    route = respx_mock.put(url).mock(
        return_value=httpx.Response(200, json={"reaction": "ok"}),
    )

    result = await auth_client.chat.react(channel, message_id)

    assert result == {"reaction": "ok"}
    req = route.calls.last.request
    body = _body(req)
    assert body["sorted_metaarray"] == [
        {"key": auth_client.identity_id, "value": ["like"]},
    ]
    assert body["upsert"] is True
    assert body["mode"] == "add"
    assert req.headers["Session-Key"] == "test-sendbird-session-key"


async def test_react_custom_reaction(auth_client, respx_mock):
    channel = "ch-react"
    message_id = 7
    url = (
        f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}"
        f"/messages/{message_id}/sorted_metaarray"
    )
    route = respx_mock.put(url).mock(return_value=httpx.Response(200, json={}))

    result = await auth_client.chat.react(channel, message_id, reaction="love")

    assert result == {}
    body = _body(route.calls.last.request)
    assert body["sorted_metaarray"][0]["value"] == ["love"]


async def test_react_error_raises(auth_client, respx_mock):
    channel = "ch-react"
    message_id = 1
    url = (
        f"{SENDBIRD_REST_BASE}/v3/group_channels/{channel}"
        f"/messages/{message_id}/sorted_metaarray"
    )
    respx_mock.put(url).mock(return_value=httpx.Response(404, json={"code": 404}))

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.chat.react(channel, message_id)
