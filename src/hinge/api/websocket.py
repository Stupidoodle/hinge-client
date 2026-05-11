"""WebSocket fan-out for real-time chat updates.

Holds the set of connected browser clients and a ``broadcast`` callable
the application layer wires into ``SendbirdWsBridge.on_event``. The
upstream Sendbird connection is started/stopped by the auth flow — this
module is purely fan-out.
"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from hinge.core.logging_config import logger as log

router = APIRouter()

_clients: set[WebSocket] = set()


async def broadcast(event_type: str, data: dict) -> None:
    """Send a typed event to every connected WebSocket client.

    Failed sockets are silently dropped from the active set so a single
    broken client never blocks delivery to the rest.
    """
    if not _clients:
        return

    message = json.dumps({"type": event_type, "data": data})
    disconnected: set[WebSocket] = set()
    for ws in _clients:
        try:
            await ws.send_text(message)
        except Exception:  # noqa: BLE001 — any send failure means drop
            disconnected.add(ws)
    _clients.difference_update(disconnected)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """Real-time chat feed.

    Browser clients open this socket and receive every Sendbird event
    SendbirdWsBridge forwards via ``broadcast``. The endpoint itself
    ignores inbound frames — it's a one-way push channel.
    """
    await websocket.accept()
    _clients.add(websocket)
    log.info("ws_chat_client_connected", client_count=len(_clients))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
        log.info("ws_chat_client_disconnected", client_count=len(_clients))
