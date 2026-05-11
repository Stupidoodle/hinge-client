"""Tests for HingeApiAdapter chat mapping helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from hinge.infrastructure.hinge.adapter import (
    HingeApiAdapter,
    _channel_from_sendbird,
    _flatten_sorted_metaarray,
    _message_from_sendbird,
)
from tests.hinge.conftest import COUNTERPARTY_CONNECTED, COUNTERPARTY_ORPHAN, MY_ID


def test_channel_from_sendbird_connected(sendbird_channels):
    raw = sendbird_channels["channels"][0]
    channel = _channel_from_sendbird(raw, MY_ID, {COUNTERPARTY_CONNECTED})
    assert channel is not None
    assert channel.channel_url == raw["channel_url"]
    assert channel.counterparty_sendbird_id == COUNTERPARTY_CONNECTED
    assert channel.is_connection_active is True
    assert channel.subject_id == COUNTERPARTY_CONNECTED
    assert channel.is_match_message is True
    assert channel.inviter_user_id == COUNTERPARTY_CONNECTED
    assert channel.created_by_user_id == COUNTERPARTY_CONNECTED
    assert channel.disappearing_message_seconds == -1
    assert channel.sms_fallback_wait_seconds == -1
    assert channel.count_preference == "all"
    assert channel.push_trigger_option == "default"
    assert channel.unread_count == 0
    assert channel.last_message_id == raw["last_message"]["message_id"]
    assert channel.last_message_at is not None
    assert channel.raw_json


def test_channel_from_sendbird_orphan(sendbird_channels):
    raw = sendbird_channels["channels"][1]
    channel = _channel_from_sendbird(raw, MY_ID, {COUNTERPARTY_CONNECTED})
    assert channel is not None
    assert channel.counterparty_sendbird_id == COUNTERPARTY_ORPHAN
    assert channel.is_connection_active is False
    assert channel.subject_id is None
    assert channel.is_match_message is False


def test_flatten_sorted_metaarray():
    arr = [
        {"key": "dedup_id", "value": ["abc"]},
        {"key": "isMatchMessage", "value": ["true"]},
        {"key": "empty", "value": []},
        {"key": "nokey"},
    ]
    out = _flatten_sorted_metaarray(arr)
    assert out == {"dedup_id": "abc", "isMatchMessage": "true"}


def test_message_from_sendbird_flattens_metaarray(sendbird_messages):
    raw = sendbird_messages["channel_0"]["messages"][0]
    channel_url = sendbird_messages["channel_0"]["channel_url"]
    msg = _message_from_sendbird(raw, channel_url=channel_url, my_id=MY_ID)
    assert msg.message_id == raw["message_id"]
    assert msg.channel_url == channel_url
    assert msg.sender_sendbird_id == COUNTERPARTY_CONNECTED
    assert msg.is_from_me is False
    assert msg.is_match_message is True
    assert msg.dedup_id == "CD4CE8DA-68AA-4EE5-97E0-C810194D0C33"
    assert msg.attempt_id == "da117c7d-8ae3-4e20-8028-11e426b5e3aa"
    assert msg.sent_from_app_version == "9.116.1"
    assert msg.sent_from_platform == "ios"
    assert msg.origin == "Native Chat"


def test_message_from_sendbird_is_from_me(sendbird_messages):
    raw = sendbird_messages["channel_0"]["messages"][1]
    msg = _message_from_sendbird(raw, channel_url="x", my_id=MY_ID)
    assert msg.is_from_me is True
    assert msg.is_match_message is False


def test_fetch_chat_state_cross_refs_connections(sendbird_channels, matches):
    client = MagicMock()
    client.identity_id = MY_ID
    client.sendbird_get_conversations = AsyncMock(return_value=sendbird_channels)
    client.get_matches = AsyncMock(return_value=matches)
    adapter = HingeApiAdapter(client)

    channels = asyncio.run(adapter.fetch_chat_state())

    assert len(channels) == 2
    actives = [c for c in channels if c.is_connection_active]
    orphans = [c for c in channels if not c.is_connection_active]
    assert len(actives) == 1
    assert len(orphans) == 1
    assert actives[0].counterparty_sendbird_id == COUNTERPARTY_CONNECTED
    assert orphans[0].subject_id is None


def test_fetch_channel_messages(sendbird_messages):
    channel_payload = sendbird_messages["channel_0"]
    client = MagicMock()
    client.identity_id = MY_ID
    client.sendbird_get_messages = AsyncMock(
        return_value={"messages": channel_payload["messages"]},
    )
    adapter = HingeApiAdapter(client)

    messages = asyncio.run(
        adapter.fetch_channel_messages(channel_payload["channel_url"]),
    )

    assert len(messages) == len(channel_payload["messages"])
    assert all(m.channel_url == channel_payload["channel_url"] for m in messages)
