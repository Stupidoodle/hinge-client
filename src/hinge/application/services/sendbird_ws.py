"""Sendbird WebSocket bridge.

Maintains a persistent WebSocket connection to Sendbird and forwards
real-time events (messages, typing, read receipts) to an ``on_event``
callback supplied at construction.
"""

import asyncio
import json
import time

import websockets
from websockets.asyncio.client import ClientConnection

from hinge.core.logging_config import logger as log

# Sendbird app
SENDBIRD_APP_ID = "3CDAD91C-1E0D-4A0D-BBEE-9671988BF9E9"
SENDBIRD_WS_BASE = f"wss://ws-{SENDBIRD_APP_ID.lower()}.sendbird.com"

# Keepalive defaults (overridden by LOGI response)
_DEFAULT_PING_INTERVAL = 15
_DEFAULT_PONG_TIMEOUT = 5

# Reconnect defaults (overridden by LOGI response)
_DEFAULT_RECONNECT_INITIAL = 2
_DEFAULT_RECONNECT_MULTIPLIER = 2
_DEFAULT_RECONNECT_MAX = 20


def _parse_command(raw: str) -> tuple[str, dict]:
    """Parse a Sendbird text frame: 4-char command + JSON body."""
    cmd = raw[:4]
    body: dict = {}
    if len(raw) > 4:
        try:
            body = json.loads(raw[4:])
        except json.JSONDecodeError:
            pass
    return cmd, body


class SendbirdWsBridge:
    """Persistent Sendbird WebSocket connection with event bridging.

    Lifecycle:
    1. ``start()`` — connects and begins listening in a background task.
    2. Events are forwarded to ``on_event(event_type, payload)``.
    3. ``stop()`` — disconnects and cancels the background task.
    """

    def __init__(
        self,
        identity_id: str,
        jwt: str,
        *,
        on_event: asyncio.coroutines | None = None,
    ) -> None:
        """Construct the bridge with Sendbird identity, JWT, and event callback."""
        self.identity_id = identity_id
        self.jwt = jwt
        # Callback for forwarding events — wired by the application layer
        self._on_event = on_event

        self._ws: ClientConnection | None = None
        self._task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._running = False

        # Config from LOGI (or defaults)
        self._ping_interval = _DEFAULT_PING_INTERVAL
        self._pong_timeout = _DEFAULT_PONG_TIMEOUT
        self._reconnect_interval = _DEFAULT_RECONNECT_INITIAL
        self._reconnect_mul = _DEFAULT_RECONNECT_MULTIPLIER
        self._reconnect_max = _DEFAULT_RECONNECT_MAX

        # Session key extracted from LOGI
        self.session_key: str = ""

    @property
    def connected(self) -> bool:
        """Return whether the WebSocket is open."""
        return self._ws is not None and self._ws.state.name == "OPEN"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the connection loop in the background."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        log.info("sendbird_ws_started", identity_id=self.identity_id[:12])

    async def stop(self) -> None:
        """Disconnect and stop the background task."""
        self._running = False
        if self._ping_task:
            self._ping_task.cancel()
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
        log.info("sendbird_ws_stopped")

    async def send_typing_start(self, channel_url: str) -> None:
        """Send TPST (typing start) through the WebSocket."""
        await self._send_command(
            "TPST",
            {
                "channel_url": channel_url,
                "time": int(time.time() * 1000),
            },
        )

    async def send_typing_end(self, channel_url: str) -> None:
        """Send TPEN (typing end) through the WebSocket."""
        await self._send_command(
            "TPEN",
            {
                "channel_url": channel_url,
                "time": int(time.time() * 1000),
            },
        )

    # ------------------------------------------------------------------
    # Connection loop with reconnect
    # ------------------------------------------------------------------

    async def _connection_loop(self) -> None:
        """Connect, listen, and reconnect on failure."""
        delay = self._reconnect_interval

        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                return
            except Exception:
                log.warning(
                    "sendbird_ws_disconnected",
                    reconnect_delay=delay,
                    exc_info=True,
                )

            if not self._running:
                return

            # Exponential backoff
            await asyncio.sleep(delay)
            delay = min(delay * self._reconnect_mul, self._reconnect_max)

    async def _connect_and_listen(self) -> None:
        """Single connection attempt: connect, process LOGI, listen."""
        uri = f"{SENDBIRD_WS_BASE}/?user_id={self.identity_id}&ai={SENDBIRD_APP_ID}"
        headers = {"SENDBIRD-WS-TOKEN": self.jwt}

        async with websockets.connect(
            uri,
            additional_headers=headers,
            ping_interval=None,
            ping_timeout=None,
        ) as ws:
            self._ws = ws

            # First message must be LOGI
            raw = await ws.recv()
            if not isinstance(raw, str) or not raw.startswith("LOGI"):
                log.error("sendbird_ws_no_logi", raw=str(raw)[:100])
                return

            self._handle_logi(raw)

            # Reset backoff on successful connect
            self._reconnect_interval = _DEFAULT_RECONNECT_INITIAL

            # Start ping keepalive
            if self._ping_task:
                self._ping_task.cancel()
            self._ping_task = asyncio.create_task(self._ping_loop())

            log.info("sendbird_ws_connected", session_key=self.session_key[:8])

            # Listen for events
            async for message in ws:
                if isinstance(message, str):
                    await self._handle_message(message)

        # Connection closed
        self._ws = None
        if self._ping_task:
            self._ping_task.cancel()

    # ------------------------------------------------------------------
    # LOGI handling
    # ------------------------------------------------------------------

    def _handle_logi(self, raw: str) -> None:
        """Parse LOGI response and extract config."""
        _, body = _parse_command(raw)
        self.session_key = body.get("key", "")
        self._ping_interval = body.get("ping_interval", _DEFAULT_PING_INTERVAL)
        self._pong_timeout = body.get("pong_timeout", _DEFAULT_PONG_TIMEOUT)

        reconnect = body.get("reconnect", {})
        self._reconnect_interval = reconnect.get(
            "interval",
            _DEFAULT_RECONNECT_INITIAL,
        )
        self._reconnect_mul = reconnect.get("mul", _DEFAULT_RECONNECT_MULTIPLIER)
        self._reconnect_max = reconnect.get(
            "max_interval",
            _DEFAULT_RECONNECT_MAX,
        )

    # ------------------------------------------------------------------
    # Ping/Pong keepalive
    # ------------------------------------------------------------------

    async def _ping_loop(self) -> None:
        """Keepalive: send PING text frames periodically.

        Sendbird servers may not reply with PONG to text pings.
        We send them to keep the connection alive (NAT/proxy timeout
        prevention) but do NOT close on missing PONG — the connection
        is considered alive as long as the recv loop is running.
        """
        try:
            while self._running and self.connected:
                await asyncio.sleep(self._ping_interval)
                if self._ws:
                    ping_ts = int(time.time() * 1000)
                    await self._ws.send(f"PING{ping_ts}\n")
        except asyncio.CancelledError:
            return
        except Exception:
            log.warning("sendbird_ws_ping_error", exc_info=True)

    # ------------------------------------------------------------------
    # Message routing
    # ------------------------------------------------------------------

    async def _handle_message(self, raw: str) -> None:
        """Route an incoming Sendbird command to the appropriate handler."""
        cmd, body = _parse_command(raw)

        if cmd == "MESG":
            await self._emit(
                "hinge_chat_message",
                {
                    "channel_url": body.get("channel_url", ""),
                    "message_id": body.get("msg_id"),
                    "message": body.get("message", ""),
                    "sender": {
                        "user_id": body.get("user", {}).get("user_id", ""),
                        "nickname": body.get("user", {}).get("nickname", ""),
                        "profile_url": body.get("user", {}).get("profile_url", ""),
                    },
                    "created_at": body.get("ts"),
                    "data": body.get("data"),
                    "sorted_metaarray": body.get("sorted_metaarray"),
                },
            )
        elif cmd == "FILE":
            await self._emit(
                "hinge_chat_file",
                {
                    "channel_url": body.get("channel_url", ""),
                    "message_id": body.get("msg_id"),
                    "sender": {
                        "user_id": body.get("user", {}).get("user_id", ""),
                        "nickname": body.get("user", {}).get("nickname", ""),
                    },
                    "file": {
                        "url": body.get("url", ""),
                        "name": body.get("name", ""),
                        "type": body.get("type", ""),
                        "data": body.get("data"),
                    },
                    "created_at": body.get("ts"),
                },
            )
        elif cmd == "READ":
            await self._emit(
                "hinge_chat_read",
                {
                    "channel_url": body.get("channel_url", ""),
                    "user_id": body.get("user", {}).get("user_id", ""),
                    "read_at": body.get("ts"),
                },
            )
        elif cmd == "TPST":
            await self._emit(
                "hinge_chat_typing",
                {
                    "channel_url": body.get("channel_url", ""),
                    "user_id": body.get("user", {}).get("user_id", ""),
                    "typing": True,
                },
            )
        elif cmd == "TPEN":
            await self._emit(
                "hinge_chat_typing",
                {
                    "channel_url": body.get("channel_url", ""),
                    "user_id": body.get("user", {}).get("user_id", ""),
                    "typing": False,
                },
            )
        elif cmd == "SYEV":
            await self._emit(
                "hinge_chat_system",
                {
                    "channel_url": body.get("channel_url", ""),
                    "category": body.get("cat"),
                    "data": body.get("data"),
                    "ts": body.get("ts"),
                },
            )
        elif cmd == "EROR":
            log.warning(
                "sendbird_ws_error",
                code=body.get("code"),
                message=body.get("message"),
            )
        # PONG, ADMM, BRDM, DLVR — logged but not forwarded
        elif cmd not in ("PONG",):
            log.debug("sendbird_ws_unhandled", cmd=cmd)

    async def _emit(self, event_type: str, data: dict) -> None:
        """Forward an event to the frontend WebSocket."""
        if self._on_event:
            try:
                await self._on_event(event_type, data)
            except Exception:
                log.warning("sendbird_ws_emit_error", exc_info=True)

    async def _send_command(self, cmd: str, body: dict) -> None:
        """Send a text command through the WebSocket."""
        if not self.connected or not self._ws:
            log.warning("sendbird_ws_send_not_connected", cmd=cmd)
            return
        frame = f"{cmd}{json.dumps(body, separators=(',', ':'))}\n"
        await self._ws.send(frame)
