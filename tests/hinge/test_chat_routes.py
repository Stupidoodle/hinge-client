"""HTTP-layer tests for the hinge /chat routes."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from hinge.api.chat import router as chat_router
from hinge.api.deps import require_hinge_auth
from hinge.application.services.chat_sync_service import SyncResult
from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.domain.models.chat_message import HingeChatMessage
from hinge.domain.models.profile import HingeProfile


def _make_channel(
    channel_url: str = "c1",
    subject_id: str | None = "111",
) -> HingeChatChannel:
    now = datetime.now(UTC)
    return HingeChatChannel(
        channel_url=channel_url,
        counterparty_sendbird_id=subject_id or "orphan",
        custom_type="",
        channel_created_at=now,
        subject_id=subject_id,
        last_message_at=now,
        raw_json='{"x": 1}',
    )


def _make_message(message_id: int = 1, channel_url: str = "c1") -> HingeChatMessage:
    return HingeChatMessage(
        message_id=message_id,
        channel_url=channel_url,
        sender_sendbird_id="111",
        is_from_me=False,
        message_type="MESG",
        body="hello world",
        data="",
        custom_type="",
        created_at=datetime.now(UTC),
        message_survival_seconds=0,
        message_retention_hour=0,
        raw_json="{}",
    )


def _make_profile(subject_id: str = "111") -> HingeProfile:
    p = HingeProfile(subject_id=subject_id, first_name="Alice")
    p.photo_urls.append("https://cdn.example.com/alice.jpg")
    return p


@pytest.fixture
def mock_container():
    channel = _make_channel()
    message = _make_message()
    profile = _make_profile()

    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.chat = MagicMock()
    uow.chat.get_channels = MagicMock(return_value=[channel])
    uow.chat.get_channel = MagicMock(return_value=channel)
    uow.chat.get_messages = MagicMock(return_value=[message])
    uow.profiles = MagicMock()
    uow.profiles.get = MagicMock(return_value=profile)

    container = MagicMock()
    type(container).uow = PropertyMock(return_value=uow)

    container.chat_sync = MagicMock()
    container.chat_sync.last_sync_at = datetime.now(UTC)
    container.chat_sync.last_result = SyncResult(
        channels_upserted=2,
        channels_marked_orphan=1,
        messages_upserted=5,
        duration_ms=123,
    )

    async def _sync_all():
        return container.chat_sync.last_result

    container.chat_sync.sync_all = _sync_all

    container._client = MagicMock()
    container._client.sendbird_session_key = "key"
    return container


@pytest.fixture
def client(mock_container):
    app = FastAPI()
    app.include_router(chat_router)
    app.dependency_overrides[require_hinge_auth] = lambda: mock_container
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_conversations_returns_enriched_channels(client):
    resp = client.get("/chat/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    out = data[0]
    # Channel fields
    assert out["channel_url"] == "c1"
    assert out["subject_id"] == "111"
    assert out["counterparty_name"] == "Alice"
    assert out["counterparty_photo_url"] == "https://cdn.example.com/alice.jpg"
    assert out["last_message_body"] == "hello world"
    assert out["raw_json"] == '{"x": 1}'


def test_get_sync_status(client):
    resp = client.get("/chat/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_result"]["channels_upserted"] == 2
    assert data["last_result"]["messages_upserted"] == 5


def test_post_sync_returns_result(client):
    resp = client.post("/chat/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["channels_upserted"] == 2
    assert data["channels_marked_orphan"] == 1


def test_get_single_channel(client):
    resp = client.get("/chat/c1")
    assert resp.status_code == 200
    assert resp.json()["channel_url"] == "c1"


def test_get_messages(client):
    resp = client.get("/chat/c1/messages?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["message_id"] == 1
    assert data[0]["body"] == "hello world"
