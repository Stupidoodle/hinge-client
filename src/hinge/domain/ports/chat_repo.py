"""Hinge chat repository port — abstract boundary for chat persistence."""

from abc import ABC, abstractmethod

from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.domain.models.chat_message import HingeChatMessage


class HingeChatRepo(ABC):
    """Abstract repository for Sendbird channel + message persistence.

    Concrete implementations live under ``hinge.infrastructure.db.repositories``;
    the application layer (services, routes) only ever talks to this port.
    """

    @abstractmethod
    def upsert_channel(self, channel: HingeChatChannel) -> None:
        """Insert or update a channel row keyed by ``channel_url``."""
        raise NotImplementedError

    @abstractmethod
    def upsert_messages(self, messages: list[HingeChatMessage]) -> int:
        """Insert or update a batch of messages. Returns the number written."""
        raise NotImplementedError

    @abstractmethod
    def get_channels(
        self,
        *,
        include_orphans: bool = False,
    ) -> list[HingeChatChannel]:
        """List all channels, optionally including unmatched (orphaned) ones."""
        raise NotImplementedError

    @abstractmethod
    def get_channel(self, channel_url: str) -> HingeChatChannel | None:
        """Fetch a single channel by ``channel_url``."""
        raise NotImplementedError

    @abstractmethod
    def get_messages(
        self,
        channel_url: str,
        *,
        limit: int = 100,
        before_ts: object | None = None,
    ) -> list[HingeChatMessage]:
        """Fetch messages for a channel, newest-first, paginated by timestamp."""
        raise NotImplementedError

    @abstractmethod
    def mark_channels_orphan(self, orphan_urls: set[str]) -> int:
        """Flag channels as unmatched. Returns the number updated."""
        raise NotImplementedError
