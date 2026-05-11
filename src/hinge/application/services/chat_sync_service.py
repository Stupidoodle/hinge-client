"""Hinge chat sync service — mirrors Sendbird channels/messages into the DB."""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from hinge.core.logging_config import logger as log
from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.infrastructure.db.unit_of_work import HingeSqlAlchemyUnitOfWork
from hinge.infrastructure.hinge.adapter import HingeApiAdapter

_PROFILE_BATCH_SIZE = 10

_SYNC_INTERVAL_SECONDS = 60
_MESSAGE_SYNC_CONCURRENCY = 5


@dataclass
class SyncResult:
    """Summary of a sync run."""

    channels_upserted: int
    channels_marked_orphan: int
    messages_upserted: int
    duration_ms: int


class ChatSyncService:
    """Mirror Sendbird chat state into the local DB."""

    def __init__(
        self,
        api: HingeApiAdapter,
        uow_factory: sessionmaker[Session],
    ) -> None:
        """Wire the service to its API adapter and SQLAlchemy session factory."""
        self._api = api
        self._uow_factory = uow_factory
        self.last_sync_at: datetime | None = None
        self.last_result: SyncResult | None = None

    def _uow(self) -> HingeSqlAlchemyUnitOfWork:
        return HingeSqlAlchemyUnitOfWork(self._uow_factory)

    async def sync_channels(self) -> SyncResult:
        """Fetch + upsert all channels, marking missing ones as orphan."""
        start = time.monotonic()
        channels = await self._api.fetch_chat_state()
        upserted, orphaned = self._persist_channels(channels)
        duration_ms = int((time.monotonic() - start) * 1000)
        result = SyncResult(
            channels_upserted=upserted,
            channels_marked_orphan=orphaned,
            messages_upserted=0,
            duration_ms=duration_ms,
        )
        self.last_sync_at = datetime.now(UTC)
        self.last_result = result
        return result

    def _persist_channels(
        self,
        channels: list[HingeChatChannel],
    ) -> tuple[int, int]:
        """Upsert channels; mark stored channels absent from the fetch as orphan."""
        fresh_urls = {c.channel_url for c in channels}
        orphaned = 0
        with self._uow() as uow:
            existing = {c.channel_url for c in uow.chat.get_channels()}
            missing = existing - fresh_urls
            if missing:
                orphaned = uow.chat.mark_channels_orphan(missing)
            for channel in channels:
                uow.chat.upsert_channel(channel)
            uow.commit()
        return len(channels), orphaned

    async def sync_messages(self, channel_url: str) -> SyncResult:
        """Fetch + upsert messages for a single channel."""
        start = time.monotonic()
        messages = await self._api.fetch_channel_messages(channel_url)
        with self._uow() as uow:
            written = uow.chat.upsert_messages(messages)
            uow.commit()
        duration_ms = int((time.monotonic() - start) * 1000)
        return SyncResult(
            channels_upserted=0,
            channels_marked_orphan=0,
            messages_upserted=written,
            duration_ms=duration_ms,
        )

    async def _backfill_counterparty_profiles(
        self, channels: list[HingeChatChannel]
    ) -> int:
        """Fetch + upsert profiles for active-connection channels not yet in DB."""
        active_sids = [
            c.subject_id for c in channels if c.is_connection_active and c.subject_id
        ]
        if not active_sids:
            return 0

        # Check which ones are already in hinge_profiles
        with self._uow() as uow:
            missing = [sid for sid in active_sids if uow.profiles.get(sid) is None]

        if not missing:
            return 0

        log.info("chat_sync_fetching_profiles", count=len(missing))
        try:
            profile_map = await self._api.get_profiles_quick(missing)
        except Exception:
            log.warning("chat_sync_profile_fetch_failed", exc_info=True)
            return 0

        if not profile_map:
            return 0

        seen: set[str] = set()
        with self._uow() as uow:
            for profile in profile_map.values():
                if profile.subject_id in seen:
                    continue
                seen.add(profile.subject_id)
                uow.profiles.add(profile)
            uow.commit()

        log.info("chat_sync_profiles_upserted", count=len(seen))
        return len(seen)

    async def sync_all(self) -> SyncResult:
        """Full sync: channels then messages for each channel (bounded parallelism)."""
        start = time.monotonic()
        channels = await self._api.fetch_chat_state()
        upserted, orphaned = self._persist_channels(channels)

        # Backfill counterparty profiles so counterparty_name is never null
        await self._backfill_counterparty_profiles(channels)

        sem = asyncio.Semaphore(_MESSAGE_SYNC_CONCURRENCY)

        async def _one(channel_url: str) -> int:
            async with sem:
                messages = await self._api.fetch_channel_messages(channel_url)
                if not messages:
                    return 0
                with self._uow() as uow:
                    written = uow.chat.upsert_messages(messages)
                    uow.commit()
                return int(written)

        counts: list[int | BaseException] = await asyncio.gather(
            *(_one(c.channel_url) for c in channels),
            return_exceptions=True,
        )
        total_messages = 0
        for c in counts:
            if isinstance(c, BaseException):
                log.warning("chat_sync_channel_failed", exc_info=c)
                continue
            total_messages += c

        duration_ms = int((time.monotonic() - start) * 1000)
        result = SyncResult(
            channels_upserted=upserted,
            channels_marked_orphan=orphaned,
            messages_upserted=total_messages,
            duration_ms=duration_ms,
        )
        self.last_sync_at = datetime.now(UTC)
        self.last_result = result
        log.info(
            "chat_sync_done",
            channels=upserted,
            orphaned=orphaned,
            messages=total_messages,
            ms=duration_ms,
        )
        return result

    async def _loop(self) -> None:
        """Background loop — runs sync_all every ~60s, swallowing errors."""
        log.info("chat_sync_loop_started", interval=_SYNC_INTERVAL_SECONDS)
        while True:
            try:
                await self.sync_all()
            except asyncio.CancelledError:
                log.info("chat_sync_loop_cancelled")
                return
            except Exception:
                log.warning("chat_sync_loop_error", exc_info=True)
            await asyncio.sleep(_SYNC_INTERVAL_SECONDS)
