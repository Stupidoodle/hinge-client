"""Tests for ChatSyncService."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hinge.infrastructure.db.metadata import metadata
from hinge.application.services.chat_sync_service import ChatSyncService
from hinge.infrastructure.db.mappers import start_hinge_mappers
from hinge.infrastructure.db.unit_of_work import HingeSqlAlchemyUnitOfWork
from hinge.infrastructure.hinge.adapter import (
    _channel_from_sendbird,
    _message_from_sendbird,
)
from tests.hinge.conftest import COUNTERPARTY_CONNECTED, MY_ID


@pytest.fixture
def uow_factory():
    start_hinge_mappers()
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def mock_adapter(sendbird_channels, sendbird_messages):
    adapter = AsyncMock()
    connection_ids = {COUNTERPARTY_CONNECTED}

    channels = [
        _channel_from_sendbird(raw, MY_ID, connection_ids)
        for raw in sendbird_channels["channels"]
    ]
    adapter.fetch_chat_state = AsyncMock(return_value=channels)

    by_url = {
        payload["channel_url"]: payload["messages"]
        for payload in sendbird_messages.values()
    }

    async def _fetch(channel_url, since_ts=0):
        msgs = by_url.get(channel_url, [])
        return [
            _message_from_sendbird(m, channel_url=channel_url, my_id=MY_ID)
            for m in msgs
        ]

    adapter.fetch_channel_messages = _fetch

    # Counterparty-profile backfill: return empty dict so the service's
    # `if not profile_map: return 0` short-circuits — the test exercises
    # channel+message sync, not the profile-backfill side path.
    adapter.get_profiles_quick = AsyncMock(return_value={})

    return adapter


def test_sync_all_persists_channels_and_messages(uow_factory, mock_adapter):
    service = ChatSyncService(api=mock_adapter, uow_factory=uow_factory)
    result = asyncio.run(service.sync_all())

    assert result.channels_upserted == 2
    assert result.messages_upserted >= 1
    assert service.last_sync_at is not None

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        channels = uow.chat.get_channels()
        all_msgs = []
        for c in channels:
            all_msgs.extend(uow.chat.get_messages(c.channel_url))
    assert len(channels) == 2
    assert len(all_msgs) == result.messages_upserted


def test_sync_all_marks_orphans(uow_factory, mock_adapter):
    # Pre-seed a channel that won't appear in the fetch
    from datetime import UTC, datetime

    from hinge.domain.models.chat_channel import HingeChatChannel

    now = datetime.now(UTC)
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.chat.upsert_channel(
            HingeChatChannel(
                channel_url="stale_channel",
                counterparty_sendbird_id="999",
                custom_type="",
                channel_created_at=now,
            ),
        )
        uow.commit()

    service = ChatSyncService(api=mock_adapter, uow_factory=uow_factory)
    result = asyncio.run(service.sync_all())

    assert result.channels_marked_orphan == 1
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        stale = uow.chat.get_channel("stale_channel")
    assert stale is not None
    assert stale.is_connection_active is False
