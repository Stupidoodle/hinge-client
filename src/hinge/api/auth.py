"""Hinge authentication endpoints with multi-session support."""

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hinge.core.logging_config import logger as log
from hinge.api.deps import get_hinge_container
from hinge.application.services.sendbird_ws import SendbirdWsBridge
from hinge.bootstrap import HingeContainer
from hinge.client import HingeClient
from hinge.error import HingeAuthError, HingeEmail2FAError

router = APIRouter(prefix="/auth", tags=["hinge-auth"])


async def _start_sendbird_bridge(container: HingeContainer) -> None:
    """Start the Sendbird WS bridge after successful auth (if not running)."""
    client = container._client
    if not client.sendbird_jwt or not client.identity_id:
        return
    if container.sendbird_ws and container.sendbird_ws.connected:
        return
    from hinge.api.websocket import broadcast

    bridge = SendbirdWsBridge(
        identity_id=client.identity_id,
        jwt=client.sendbird_jwt,
        on_event=broadcast,
    )
    container.sendbird_ws = bridge
    await bridge.start()
    log.info("sendbird_ws_started_post_auth")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ConnectRequest(BaseModel):
    """Request body for starting SMS OTP flow."""

    phone_number: str


class OtpRequest(BaseModel):
    """Request body for submitting OTP code."""

    otp_code: str


class EmailCodeRequest(BaseModel):
    """Request body for submitting email 2FA code."""

    email_code: str
    case_id: str


class SwitchSessionRequest(BaseModel):
    """Request body for switching active session."""

    phone_number: str


class AuthStatusResponse(BaseModel):
    """Full auth status with state machine."""

    auth_state: str  # unauthenticated | pending_otp | pending_email | authenticated
    connected: bool
    phone_number: str
    identity_id: str | None = None
    token_expires: str | None = None
    sendbird_connected: bool = False
    # Email 2FA context (populated when auth_state == "pending_email")
    pending_email: str | None = None
    pending_case_id: str | None = None
    # Like budget (populated via /likelimit health check)
    likes_left: int | None = None
    superlikes_left: int | None = None


class SessionInfo(BaseModel):
    """Saved session metadata."""

    phone_number: str
    identity_id: str
    auth_state: str
    """One of: authenticated, expired, pending_otp, pending_email, unauthenticated."""
    token_expires: str | None = None
    is_active: bool = False
    needs_reauth: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    container: HingeContainer = Depends(get_hinge_container),
) -> AuthStatusResponse:
    """Return current auth state, phone number, token info, and like budget.

    Uses ``/likelimit`` as the authoritative session health check.
    If the token looks valid locally, pings ``/likelimit`` to confirm.
    """
    client = container._client

    connected = False
    likes_left: int | None = None
    superlikes_left: int | None = None

    if client.hinge_token:
        token_not_expired = client.hinge_token_expires > datetime.now(timezone.utc)
        if token_not_expired:
            # Authoritative check: /likelimit
            limit = await client.check_session_health()
            if limit is not None:
                connected = True
                client.auth_state = HingeClient.AUTH_AUTHENTICATED
                likes_left = limit.likes_left
                superlikes_left = limit.super_likes_left
            else:
                # /likelimit returned 401 — session is dead
                client.auth_state = HingeClient.AUTH_UNAUTHENTICATED
        elif client.auth_state == HingeClient.AUTH_AUTHENTICATED:
            client.auth_state = HingeClient.AUTH_UNAUTHENTICATED

    pending_email = None
    pending_case_id = None
    if client._pending_email_2fa:
        pending_email = client._pending_email_2fa.get("email")
        pending_case_id = client._pending_email_2fa.get("case_id")

    return AuthStatusResponse(
        auth_state=client.auth_state,
        connected=connected,
        phone_number=client.phone_number,
        identity_id=client.identity_id if connected else None,
        token_expires=(client.hinge_token_expires.isoformat() if connected else None),
        sendbird_connected=(bool(client.sendbird_session_key) if connected else False),
        pending_email=pending_email,
        pending_case_id=pending_case_id,
        likes_left=likes_left,
        superlikes_left=superlikes_left,
    )


@router.post("/connect")
async def connect(
    body: ConnectRequest,
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Start SMS OTP flow for a phone number.

    If switching to a different phone number, loads or creates
    the session file for that number.
    """
    client = container._client

    # Switch session if phone number changed
    if body.phone_number != client.phone_number:
        log.info("auth_session_switch", phone=body.phone_number)
        client.switch_session(body.phone_number)

    log.info("auth_connect_start", phone=client.phone_number)
    try:
        await client.initiate_login()
        return {
            "success": True,
            "auth_state": client.auth_state,
            "phone_number": client.phone_number,
        }
    except HingeAuthError as e:
        return {
            "success": False,
            "auth_state": client.auth_state,
            "phone_number": client.phone_number,
            "error": str(e),
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "auth_state": client.auth_state,
            "phone_number": client.phone_number,
            "error": f"Hinge API error: {e.response.status_code}",
        }


@router.post("/otp")
async def submit_otp(
    body: OtpRequest,
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Submit OTP code received via SMS."""
    log.info("auth_otp_submit")
    try:
        await container._client.submit_otp(body.otp_code)
        await _start_sendbird_bridge(container)
        log.info("auth_otp_success", state=container._client.auth_state)
        return {
            "success": True,
            "auth_state": container._client.auth_state,
        }
    except HingeEmail2FAError as e:
        log.warning("auth_otp_needs_email_2fa", email=e.email)
        return {
            "success": False,
            "auth_state": container._client.auth_state,
            "needs_email_2fa": True,
            "case_id": e.case_id,
            "email": e.email,
        }
    except HingeAuthError as e:
        return {
            "success": False,
            "auth_state": container._client.auth_state,
            "error": str(e),
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "auth_state": container._client.auth_state,
            "error": f"Hinge API error: {e.response.status_code}",
        }


@router.post("/email-code")
async def submit_email_code(
    body: EmailCodeRequest,
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Submit email 2FA verification code."""
    try:
        await container._client.submit_email_code(
            body.email_code,
            body.case_id,
        )
        await _start_sendbird_bridge(container)
        return {
            "success": True,
            "auth_state": container._client.auth_state,
        }
    except HingeAuthError as e:
        return {
            "success": False,
            "auth_state": container._client.auth_state,
            "error": str(e),
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "auth_state": container._client.auth_state,
            "error": f"Hinge API error: {e.response.status_code}",
        }


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    container: HingeContainer = Depends(get_hinge_container),
    refresh: bool = False,
) -> list[SessionInfo]:
    """List all saved Hinge sessions.

    Pass ``?refresh=true`` to trigger preflight token refresh for
    sessions expiring within 14 days before listing.
    """
    if refresh:
        await HingeClient.refresh_all_sessions(threshold_days=14)

    sessions = HingeClient.list_sessions()
    client = container._client
    active_phone = client.phone_number
    result: list[SessionInfo] = []
    for s in sessions:
        is_current = s["phone_number"] == active_phone
        if is_current:
            # Use in-memory truth for the active session
            if (
                client.auth_state == HingeClient.AUTH_AUTHENTICATED
                and client.hinge_token
                and client.hinge_token_expires > datetime.now(timezone.utc)
            ):
                auth_state = "authenticated"
            elif client.hinge_token and client.hinge_token_expires <= datetime.now(
                timezone.utc,
            ):
                auth_state = "expired"
            else:
                auth_state = client.auth_state
            needs_reauth = auth_state in (
                "unauthenticated",
                "expired",
            )
        else:
            auth_state = s.get("auth_state", "unauthenticated")
            needs_reauth = s.get("needs_reauth", True)

        result.append(
            SessionInfo(
                phone_number=s["phone_number"],
                identity_id=s.get("identity_id", ""),
                auth_state=auth_state,
                token_expires=s.get("token_expires"),
                is_active=is_current and auth_state == "authenticated",
                needs_reauth=needs_reauth,
            ),
        )
    return result


@router.post("/sessions/switch")
async def switch_session(
    body: SwitchSessionRequest,
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Switch active session to a different phone number."""
    container._client.switch_session(body.phone_number)
    client = container._client
    connected = bool(
        client.hinge_token,
    ) and client.hinge_token_expires > datetime.now(timezone.utc)
    return {
        "success": True,
        "phone_number": client.phone_number,
        "auth_state": client.auth_state,
        "connected": connected,
    }
