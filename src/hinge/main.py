"""FastAPI application entry point for the Hinge API.

Run with::

    uv run uvicorn hinge.main:app --reload --port 8000
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hinge.api.deps import set_hinge_container
from hinge.api.error_handlers import register_hinge_error_handlers
from hinge.api.router import router as hinge_router
from hinge.api.websocket import broadcast
from hinge.application.services.rejection_scheduler import run_scheduled_scans
from hinge.application.services.sendbird_ws import SendbirdWsBridge
from hinge.bootstrap import bootstrap_hinge
from hinge.client import HingeClient
from hinge.core.config import get_settings
from hinge.core.logging_config import logger as log

_start_time: float = 0.0


async def _preflight_session_refresh() -> None:
    """Refresh any persisted Hinge sessions expiring within 14 days."""
    try:
        results = await HingeClient.refresh_all_sessions(threshold_days=14)
        if results:
            log.info("preflight_hinge_refresh_done", results=results)
    except Exception:
        log.warning("preflight_hinge_refresh_error", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap the DDD container on startup; tear it down on shutdown."""
    global _start_time  # noqa: PLW0603
    _start_time = time.time()

    settings = get_settings()
    container = bootstrap_hinge(settings=settings)
    set_hinge_container(container)
    log.info(
        "hinge_app_started",
        phone_configured=bool(settings.HINGE_PHONE_NUMBER),
        auth_state=container._client.auth_state,
    )

    # Preflight: refresh any Hinge sessions expiring within 14 days.
    # Fire-and-forget so it doesn't block startup.
    asyncio.create_task(_preflight_session_refresh())

    # Sendbird WebSocket bridge — only if the client is already authenticated.
    # Otherwise wired post-auth by /auth/connect → /auth/otp flow.
    client = container._client
    if client.sendbird_jwt and client.identity_id:
        bridge = SendbirdWsBridge(
            identity_id=client.identity_id,
            jwt=client.sendbird_jwt,
            on_event=broadcast,
        )
        container.sendbird_ws = bridge
        await bridge.start()

    # Scheduled rejection scan
    scan_task = asyncio.create_task(run_scheduled_scans(container))

    # Background chat sync loop (every ~60s)
    chat_sync_task: asyncio.Task | None = None
    if container.chat_sync is not None:
        chat_sync_task = asyncio.create_task(container.chat_sync._loop())

    try:
        yield
    finally:
        scan_task.cancel()
        if chat_sync_task is not None:
            chat_sync_task.cancel()
        if container.sendbird_ws:
            await container.sendbird_ws.stop()
        log.info("hinge_app_stopped")


app = FastAPI(
    title="Hinge API",
    description="Reverse-engineered Hinge mobile API — REST + WebSocket surface.",
    version="0.1.0",
    lifespan=lifespan,
)

register_hinge_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://localhost:\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hinge_router)


@app.get("/health")
async def health() -> dict:
    """Liveness probe — returns uptime in seconds."""
    uptime_s = round(time.time() - _start_time) if _start_time else 0
    return {"status": "ok", "version": "0.1.0", "uptime_seconds": uptime_s}
