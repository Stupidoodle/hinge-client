"""Hinge chat endpoints.

Reads are served from the local Sendbird mirror DB (see ChatSyncService).
Writes still go through Hinge's POST /message/send (harassment detection) and
Sendbird REST (read receipts, reactions). Typing indicators use the
persistent Sendbird WebSocket bridge.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from hinge.core.logging_config import logger as log
from hinge.api.deps import require_hinge_auth
from hinge.application.services.chat_sync_service import ChatSyncService, SyncResult
from hinge.bootstrap import HingeContainer
from hinge.domain.models.chat_channel import HingeChatChannel

router = APIRouter(prefix="/chat", tags=["hinge-chat"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChannelOut(BaseModel):
    """A Sendbird chat channel, mirrored from the local DB."""

    model_config = ConfigDict(from_attributes=True)

    channel_url: str
    subject_id: str | None
    counterparty_sendbird_id: str
    counterparty_name: str | None = None
    counterparty_photo_url: str | None = None
    last_message_body: str | None = None
    is_connection_active: bool
    is_match_message: bool
    inviter_user_id: str | None
    created_by_user_id: str | None
    custom_type: str
    disappearing_message_seconds: int
    disappearing_triggered_by_read: bool
    sms_fallback_wait_seconds: int
    count_preference: str
    push_trigger_option: str
    has_ai_bot: bool
    has_bot: bool
    is_ai_agent_channel: bool
    ignore_profanity_filter: bool
    unread_count: int
    last_message_id: int | None
    last_message_at: datetime | None
    channel_created_at: datetime
    first_synced_at: datetime
    last_synced_at: datetime
    raw_json: str


class MessageOut(BaseModel):
    """A Sendbird chat message, mirrored from the local DB."""

    model_config = ConfigDict(from_attributes=True)

    message_id: int
    channel_url: str
    sender_sendbird_id: str
    is_from_me: bool
    message_type: str
    body: str
    data: str
    custom_type: str
    created_at: datetime
    updated_at: datetime | None
    dedup_id: str | None
    attempt_id: str | None
    is_match_message: bool
    origin: str | None
    sent_from_app_version: str | None
    sent_from_platform: str | None
    file_url: str | None
    file_type: str | None
    file_size: int | None
    file_name: str | None
    is_removed: bool
    is_silent: bool
    is_op_msg: bool
    message_survival_seconds: int
    message_retention_hour: int
    raw_json: str


class SyncResultOut(BaseModel):
    """Result of a chat sync run."""

    channels_upserted: int
    channels_marked_orphan: int
    messages_upserted: int
    duration_ms: int


class ChannelSyncStatus(BaseModel):
    """Status of the background chat sync loop."""

    last_sync_at: datetime | None
    last_result: SyncResultOut | None


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    subject_id: str
    message: str
    match_message: bool = False


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    message_id: str
    created_at: int


class UnreadCountResponse(BaseModel):
    """Unread channel count."""

    unread_channel_count: int


class MarkReadResponse(BaseModel):
    """Response after marking a channel as read."""

    success: bool


class ReactRequest(BaseModel):
    """Request body for reacting to a message."""

    reaction: str = "like"


class ReactResponse(BaseModel):
    """Response after adding a reaction."""

    success: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_sendbird(container: HingeContainer) -> None:
    """Raise 503 if Sendbird session key is missing."""
    if not container._client.sendbird_session_key:
        raise HTTPException(
            status_code=503,
            detail="Sendbird not connected — re-authenticate to obtain session key",
        )


def _require_chat_sync(container: HingeContainer) -> ChatSyncService:
    """Raise 503 if chat sync service is not wired."""
    chat_sync = getattr(container, "chat_sync", None)
    if chat_sync is None:
        raise HTTPException(
            status_code=503,
            detail="Chat sync service not running",
        )
    return chat_sync


def _to_sync_result(result: SyncResult | None) -> SyncResultOut | None:
    if result is None:
        return None
    return SyncResultOut(
        channels_upserted=result.channels_upserted,
        channels_marked_orphan=result.channels_marked_orphan,
        messages_upserted=result.messages_upserted,
        duration_ms=result.duration_ms,
    )


def _build_channel_out(
    channel: HingeChatChannel,
    container: HingeContainer,
) -> ChannelOut:
    """Enrich a domain channel with counterparty profile info + last message."""
    name: str | None = None
    photo: str | None = None
    body: str | None = None

    with container.uow as uow:
        if channel.subject_id:
            profile = uow.profiles.get(channel.subject_id)
            if profile:
                name = profile.first_name or None
                if profile.photo_urls:
                    photo = profile.photo_urls[0]
        latest = uow.chat.get_messages(channel.channel_url, limit=1)
        if latest:
            body = (latest[0].body or "")[:120] or None

    out = ChannelOut.model_validate(channel)
    out.counterparty_name = name
    out.counterparty_photo_url = photo
    out.last_message_body = body
    return out


# ---------------------------------------------------------------------------
# Sync status
# ---------------------------------------------------------------------------


@router.get("/sync", response_model=ChannelSyncStatus)
async def get_sync_status(
    container: HingeContainer = Depends(require_hinge_auth),
) -> ChannelSyncStatus:
    """Return the current chat sync state."""
    chat_sync = _require_chat_sync(container)
    return ChannelSyncStatus(
        last_sync_at=chat_sync.last_sync_at,
        last_result=_to_sync_result(chat_sync.last_result),
    )


@router.post("/sync", response_model=SyncResultOut)
async def trigger_sync(
    container: HingeContainer = Depends(require_hinge_auth),
) -> SyncResultOut:
    """Run a full chat sync inline and return the result."""
    _require_sendbird(container)
    chat_sync = _require_chat_sync(container)
    result = await chat_sync.sync_all()
    return _to_sync_result(result)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Conversations (DB-backed)
# ---------------------------------------------------------------------------


@router.get("/conversations", response_model=list[ChannelOut])
async def get_conversations(
    include_orphans: bool = Query(default=True),
    container: HingeContainer = Depends(require_hinge_auth),
) -> list[ChannelOut]:
    """List mirrored chat channels, newest activity first."""
    with container.uow as uow:
        channels = uow.chat.get_channels(include_orphans=include_orphans)
    return [_build_channel_out(c, container) for c in channels]


@router.get("/unread", response_model=UnreadCountResponse)
async def get_unread_count(
    container: HingeContainer = Depends(require_hinge_auth),
) -> UnreadCountResponse:
    """Get unread channel count from Sendbird (live — not from DB)."""
    _require_sendbird(container)
    data = await container._client.sendbird_unread_count()
    return UnreadCountResponse(
        unread_channel_count=data.get("unread_count", 0),
    )


@router.post("/{channel_url}/typing")
async def send_typing_indicator(
    channel_url: str,
    typing: bool = Query(default=True),
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict[str, bool]:
    """Send typing start/end via the Sendbird WebSocket."""
    bridge = container.sendbird_ws
    if not bridge or not bridge.connected:
        raise HTTPException(
            status_code=503,
            detail="Sendbird WebSocket not connected",
        )
    if typing:
        await bridge.send_typing_start(channel_url)
    else:
        await bridge.send_typing_end(channel_url)
    return {"success": True}


# --- Channel-scoped routes (/{channel_url} catch-all — must be LAST) ---


@router.get("/{channel_url}", response_model=ChannelOut)
async def get_channel(
    channel_url: str,
    container: HingeContainer = Depends(require_hinge_auth),
) -> ChannelOut:
    """Fetch a single mirrored channel."""
    with container.uow as uow:
        channel = uow.chat.get_channel(channel_url)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return _build_channel_out(channel, container)


@router.get("/{channel_url}/messages", response_model=list[MessageOut])
async def get_messages(
    channel_url: str,
    limit: int = Query(default=100, ge=1, le=500),
    before: datetime | None = Query(default=None),
    container: HingeContainer = Depends(require_hinge_auth),
) -> list[MessageOut]:
    """Fetch mirrored message history for a channel, newest first."""
    with container.uow as uow:
        messages = uow.chat.get_messages(
            channel_url,
            limit=limit,
            before_ts=before,
        )
    return [MessageOut.model_validate(m) for m in messages]


@router.post("/{channel_url}/send", response_model=SendMessageResponse)
async def send_message(
    channel_url: str,
    body: SendMessageRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> SendMessageResponse:
    """Send a text message via Hinge API (server-side harassment check)."""
    result = await container._client.hinge_send_message(
        subject_id=body.subject_id,
        message=body.message,
        match_message=body.match_message,
    )
    log.info("chat_message_sent", channel=channel_url[:16], length=len(body.message))
    return SendMessageResponse(
        message_id=result.get("messageId", ""),
        created_at=result.get("createdAt", 0),
    )


@router.post(
    "/{channel_url}/read",
    response_model=MarkReadResponse,
)
async def mark_as_read(
    channel_url: str,
    container: HingeContainer = Depends(require_hinge_auth),
) -> MarkReadResponse:
    """Mark all messages as read in a Sendbird channel."""
    _require_sendbird(container)
    await container._client.sendbird_mark_as_read(channel_url)
    log.debug("chat_marked_read", channel=channel_url[:16])
    return MarkReadResponse(success=True)


@router.post(
    "/{channel_url}/{message_id}/react",
    response_model=ReactResponse,
)
async def react_to_message(
    channel_url: str,
    message_id: int,
    body: ReactRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> ReactResponse:
    """Add a reaction to a message via sorted_metaarray (Hinge convention)."""
    _require_sendbird(container)
    await container._client.sendbird_react(
        channel_url,
        message_id,
        reaction=body.reaction,
    )
    log.info("chat_reacted", channel=channel_url[:16], msg_id=message_id)
    return ReactResponse(success=True)
