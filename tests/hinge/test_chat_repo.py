"""Tests for the SqlHingeChatRepo."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hinge.infrastructure.db.metadata import metadata
from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.domain.models.chat_message import HingeChatMessage
from hinge.infrastructure.db.mappers import start_hinge_mappers
from hinge.infrastructure.db.unit_of_work import HingeSqlAlchemyUnitOfWork


@pytest.fixture
def uow_factory():
    start_hinge_mappers()
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _make_channel(url: str, subject_id: str | None = "111") -> HingeChatChannel:
    now = datetime.now(UTC)
    return HingeChatChannel(
        channel_url=url,
        counterparty_sendbird_id=subject_id or "orphan",
        custom_type="",
        channel_created_at=now,
        subject_id=subject_id,
        last_message_at=now,
    )


def _make_message(
    message_id: int,
    channel_url: str,
    created_at: datetime,
) -> HingeChatMessage:
    return HingeChatMessage(
        message_id=message_id,
        channel_url=channel_url,
        sender_sendbird_id="111",
        is_from_me=False,
        message_type="MESG",
        body="hi",
        data="",
        custom_type="",
        created_at=created_at,
        message_survival_seconds=0,
        message_retention_hour=0,
        raw_json="",
    )


def test_upsert_channel_is_idempotent(uow_factory):
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.chat.upsert_channel(_make_channel("c1"))
        uow.chat.upsert_channel(_make_channel("c1"))
        uow.commit()
        channels = uow.chat.get_channels()
    assert len(channels) == 1


def test_upsert_messages_is_idempotent(uow_factory):
    now = datetime.now(UTC)
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.chat.upsert_channel(_make_channel("c1"))
        uow.chat.upsert_messages(
            [
                _make_message(1, "c1", now),
                _make_message(2, "c1", now - timedelta(minutes=1)),
            ],
        )
        uow.chat.upsert_messages([_make_message(1, "c1", now)])
        uow.commit()
        msgs = uow.chat.get_messages("c1")
    assert {m.message_id for m in msgs} == {1, 2}
    # Newest-first
    assert msgs[0].message_id == 1


def test_mark_channels_orphan(uow_factory):
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.chat.upsert_channel(_make_channel("c1"))
        uow.chat.upsert_channel(_make_channel("c2"))
        uow.commit()
        marked = uow.chat.mark_channels_orphan({"c1"})
        uow.commit()
        channels = uow.chat.get_channels()
    by_url = {c.channel_url: c for c in channels}
    assert marked == 1
    assert by_url["c1"].is_connection_active is False
    assert by_url["c2"].is_connection_active is True


def test_get_messages_respects_before_ts(uow_factory):
    now = datetime.now(UTC)
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.chat.upsert_channel(_make_channel("c1"))
        uow.chat.upsert_messages(
            [
                _make_message(1, "c1", now),
                _make_message(2, "c1", now - timedelta(hours=1)),
                _make_message(3, "c1", now - timedelta(hours=2)),
            ],
        )
        uow.commit()
        older = uow.chat.get_messages("c1", before_ts=now - timedelta(minutes=30))
    assert [m.message_id for m in older] == [2, 3]


def test_get_channels_include_orphans_toggle(uow_factory):
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.chat.upsert_channel(_make_channel("c1"))
        uow.chat.upsert_channel(_make_channel("c2"))
        uow.chat.mark_channels_orphan({"c1"})
        uow.commit()
        all_ = uow.chat.get_channels(include_orphans=True)
        active = uow.chat.get_channels(include_orphans=False)
    assert {c.channel_url for c in all_} == {"c1", "c2"}
    assert {c.channel_url for c in active} == {"c2"}
