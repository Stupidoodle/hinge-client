"""SQLAlchemy Hinge chat repository."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.domain.models.chat_message import HingeChatMessage
from hinge.infrastructure.db.tables.chat_channel import hinge_chat_channel_table
from hinge.infrastructure.db.tables.chat_message import hinge_chat_message_table


def _channel_to_row(c: HingeChatChannel) -> dict[str, object]:
    return {
        "channel_url": c.channel_url,
        "subject_id": c.subject_id,
        "counterparty_sendbird_id": c.counterparty_sendbird_id,
        "is_connection_active": c.is_connection_active,
        "is_match_message": c.is_match_message,
        "inviter_user_id": c.inviter_user_id,
        "created_by_user_id": c.created_by_user_id,
        "custom_type": c.custom_type,
        "disappearing_message_seconds": c.disappearing_message_seconds,
        "disappearing_triggered_by_read": c.disappearing_triggered_by_read,
        "sms_fallback_wait_seconds": c.sms_fallback_wait_seconds,
        "count_preference": c.count_preference,
        "push_trigger_option": c.push_trigger_option,
        "has_ai_bot": c.has_ai_bot,
        "has_bot": c.has_bot,
        "is_ai_agent_channel": c.is_ai_agent_channel,
        "ignore_profanity_filter": c.ignore_profanity_filter,
        "unread_count": c.unread_count,
        "last_message_id": c.last_message_id,
        "last_message_at": c.last_message_at,
        "channel_created_at": c.channel_created_at,
        "first_synced_at": c.first_synced_at,
        "last_synced_at": c.last_synced_at,
        "raw_json": c.raw_json,
    }


def _message_to_row(m: HingeChatMessage) -> dict[str, object]:
    return {
        "message_id": m.message_id,
        "channel_url": m.channel_url,
        "sender_sendbird_id": m.sender_sendbird_id,
        "is_from_me": m.is_from_me,
        "message_type": m.message_type,
        "body": m.body,
        "data": m.data,
        "custom_type": m.custom_type,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
        "dedup_id": m.dedup_id,
        "attempt_id": m.attempt_id,
        "is_match_message": m.is_match_message,
        "origin": m.origin,
        "sent_from_app_version": m.sent_from_app_version,
        "sent_from_platform": m.sent_from_platform,
        "file_url": m.file_url,
        "file_type": m.file_type,
        "file_size": m.file_size,
        "file_name": m.file_name,
        "is_removed": m.is_removed,
        "is_silent": m.is_silent,
        "is_op_msg": m.is_op_msg,
        "message_survival_seconds": m.message_survival_seconds,
        "message_retention_hour": m.message_retention_hour,
        "raw_json": m.raw_json,
    }


class SqlHingeChatRepo:
    """SQLAlchemy-backed Hinge chat repository."""

    def __init__(self, session: Session) -> None:
        """Bind this repository to a SQLAlchemy session."""
        self._session = session

    def upsert_channel(self, channel: HingeChatChannel) -> None:
        """INSERT OR REPLACE the channel row."""
        row = _channel_to_row(channel)
        stmt = sqlite_insert(hinge_chat_channel_table).values(**row)
        update_cols = {k: stmt.excluded[k] for k in row if k != "channel_url"}
        stmt = stmt.on_conflict_do_update(
            index_elements=["channel_url"],
            set_=update_cols,
        )
        self._session.execute(stmt)

    def upsert_messages(self, messages: list[HingeChatMessage]) -> int:
        """Bulk upsert messages. Returns count written."""
        if not messages:
            return 0
        rows = [_message_to_row(m) for m in messages]
        stmt = sqlite_insert(hinge_chat_message_table)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in hinge_chat_message_table.columns
            if col.name != "message_id"
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["message_id"],
            set_=update_cols,
        )
        self._session.execute(stmt, rows)
        return len(rows)

    def get_channels(
        self,
        *,
        include_orphans: bool = True,
    ) -> list[HingeChatChannel]:
        """List all channels, ordered by last_message_at DESC."""
        stmt = select(HingeChatChannel)
        if not include_orphans:
            stmt = stmt.where(
                hinge_chat_channel_table.c.is_connection_active.is_(True),
            )
        stmt = stmt.order_by(hinge_chat_channel_table.c.last_message_at.desc())
        return list(self._session.execute(stmt).scalars())

    def get_channel(self, channel_url: str) -> HingeChatChannel | None:
        """Get a channel by URL."""
        return self._session.get(HingeChatChannel, channel_url)

    def get_messages(
        self,
        channel_url: str,
        *,
        limit: int = 100,
        before_ts: datetime | None = None,
    ) -> list[HingeChatMessage]:
        """Get messages for a channel, newest first."""
        stmt = select(HingeChatMessage).where(
            hinge_chat_message_table.c.channel_url == channel_url,
        )
        if before_ts is not None:
            stmt = stmt.where(hinge_chat_message_table.c.created_at < before_ts)
        stmt = stmt.order_by(hinge_chat_message_table.c.created_at.desc()).limit(
            limit,
        )
        return list(self._session.execute(stmt).scalars())

    def mark_channels_orphan(self, orphan_urls: set[str]) -> int:
        """Mark channels as inactive. Returns rowcount."""
        if not orphan_urls:
            return 0
        stmt = (
            update(hinge_chat_channel_table)
            .where(hinge_chat_channel_table.c.channel_url.in_(orphan_urls))
            .values(is_connection_active=False)
        )
        return self._session.execute(stmt).rowcount
