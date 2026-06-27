"""Unit tests for HingeClient auth + token lifecycle (client/_core.py).

Covers: initiate_login, submit_otp, submit_email_code,
_authenticate_with_sendbird, ensure_fresh_token, _token_expires_within,
check_session_health, is_session_valid, _get_default_headers, and the module
functions _derive_auth_state + _preflight_refresh_session.

Everything is offline: HTTP is mocked with respx, the Sendbird websocket and
``asyncio.sleep`` are mocked with unittest.mock.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

import hinge.client._core as client_core
from hinge.error import HingeAuthError, HingeEmail2FAError


def _iso(delta_days: float) -> str:
    """ISO-8601 timestamp ``delta_days`` from now (UTC)."""
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat()


class _FakeWS:
    """Minimal async-context-manager stand-in for a websockets connection."""

    def __init__(self, recv_value: str) -> None:
        self._recv_value = recv_value

    async def __aenter__(self) -> _FakeWS:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def recv(self) -> str:
        return self._recv_value


# --------------------------------------------------------------------------- #
# _get_default_headers
# --------------------------------------------------------------------------- #


def test_get_default_headers_with_token(auth_client):
    headers = auth_client._get_default_headers()
    assert headers["Authorization"] == "Bearer test-hinge-token"
    assert headers["X-Session-Id"] == auth_client.session_id
    assert headers["X-Device-Id"] == auth_client.device_id
    assert headers["X-Install-Id"] == auth_client.install_id
    assert "X-App-Version" in headers


def test_get_default_headers_without_token(client):
    headers = client._get_default_headers()
    assert "Authorization" not in headers
    assert headers["X-Device-Platform"] == "iOS"
    assert headers["X-Session-Id"] == client.session_id


# --------------------------------------------------------------------------- #
# _token_expires_within
# --------------------------------------------------------------------------- #


def test_token_expires_within_no_token(client):
    assert client._token_expires_within() is False


def test_token_expires_within_no_expiry(auth_client):
    auth_client.hinge_token_expires = None
    assert auth_client._token_expires_within() is False


def test_token_expires_within_far_future(auth_client):
    # auth_client token is 90 days out — not within the 7-day window
    assert auth_client._token_expires_within(days=7) is False


def test_token_expires_within_soon(auth_client):
    auth_client.hinge_token_expires = datetime.now(timezone.utc) + timedelta(days=1)
    assert auth_client._token_expires_within(days=7) is True


# --------------------------------------------------------------------------- #
# ensure_fresh_token
# --------------------------------------------------------------------------- #


async def test_ensure_fresh_token_not_authenticated(client, respx_mock):
    # Fresh client has no token -> early return, no HTTP.
    await client.ensure_fresh_token()
    assert client.hinge_token == ""
    assert respx_mock.calls.call_count == 0


async def test_ensure_fresh_token_not_expiring(auth_client, respx_mock):
    # Authenticated but token is far in the future -> second early return.
    await auth_client.ensure_fresh_token()
    assert auth_client.hinge_token == "test-hinge-token"
    assert respx_mock.calls.call_count == 0


async def test_ensure_fresh_token_refresh_success(auth_client, base_url, respx_mock):
    auth_client.hinge_token_expires = datetime.now(timezone.utc) + timedelta(days=1)
    new_expires = _iso(90)
    route = respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(
            201,
            json={"token": "new-token", "identityId": "new-id", "expires": new_expires},
        ),
    )
    await auth_client.ensure_fresh_token()
    assert route.called
    assert auth_client.hinge_token == "new-token"
    assert auth_client.identity_id == "new-id"
    assert auth_client.hinge_token_expires == datetime.fromisoformat(new_expires)


async def test_ensure_fresh_token_refresh_non_201(auth_client, base_url, respx_mock):
    auth_client.hinge_token_expires = datetime.now(timezone.utc) + timedelta(days=1)
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(400, text="nope"),
    )
    await auth_client.ensure_fresh_token()
    # Token left untouched on failure.
    assert auth_client.hinge_token == "test-hinge-token"


async def test_ensure_fresh_token_refresh_exception(auth_client, base_url, respx_mock):
    auth_client.hinge_token_expires = datetime.now(timezone.utc) + timedelta(days=1)
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        side_effect=httpx.ConnectError("boom"),
    )
    await auth_client.ensure_fresh_token()
    assert auth_client.hinge_token == "test-hinge-token"


# --------------------------------------------------------------------------- #
# initiate_login
# --------------------------------------------------------------------------- #


async def test_initiate_login_not_installed(client, base_url, respx_mock):
    install = respx_mock.post(f"{base_url}/identity/install").mock(
        return_value=httpx.Response(200, json={}),
    )
    initiate = respx_mock.post(f"{base_url}/auth/sms/v2/initiate").mock(
        return_value=httpx.Response(200, json={}),
    )
    assert client.installed is False
    await client.initiate_login()
    assert install.called
    assert initiate.called
    assert client.installed is True
    assert client.auth_state == client.AUTH_PENDING_OTP


async def test_initiate_login_already_installed(client, base_url, respx_mock):
    client.installed = True
    install = respx_mock.post(f"{base_url}/identity/install").mock(
        return_value=httpx.Response(200, json={}),
    )
    initiate = respx_mock.post(f"{base_url}/auth/sms/v2/initiate").mock(
        return_value=httpx.Response(200, json={}),
    )
    await client.initiate_login()
    assert not install.called
    assert initiate.called
    assert client.auth_state == client.AUTH_PENDING_OTP


async def test_initiate_login_raises_on_error(client, base_url, respx_mock):
    client.installed = True
    respx_mock.post(f"{base_url}/auth/sms/v2/initiate").mock(
        return_value=httpx.Response(500, json={}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.initiate_login()
    assert client.auth_state == client.AUTH_UNAUTHENTICATED


# --------------------------------------------------------------------------- #
# submit_otp
# --------------------------------------------------------------------------- #


async def test_submit_otp_success(client, base_url, respx_mock):
    expires = _iso(90)
    respx_mock.post(f"{base_url}/auth/sms/v2").mock(
        return_value=httpx.Response(
            200,
            json={"identityId": "id-1", "token": "tok-1", "expires": expires},
        ),
    )
    client._authenticate_with_sendbird = AsyncMock()
    await client.submit_otp("123456")
    assert client.hinge_token == "tok-1"
    assert client.identity_id == "id-1"
    assert client.auth_state == client.AUTH_AUTHENTICATED
    client._authenticate_with_sendbird.assert_awaited_once()


async def test_submit_otp_email_2fa_required(client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/auth/sms/v2").mock(
        return_value=httpx.Response(
            412,
            json={"caseId": "case-1", "email": "user@example.com"},
        ),
    )
    with pytest.raises(HingeEmail2FAError) as excinfo:
        await client.submit_otp("000000")
    assert excinfo.value.case_id == "case-1"
    assert excinfo.value.email == "user@example.com"
    assert client.auth_state == client.AUTH_PENDING_EMAIL
    assert client._pending_email_2fa == {
        "case_id": "case-1",
        "email": "user@example.com",
    }


async def test_submit_otp_412_missing_fields(client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/auth/sms/v2").mock(
        return_value=httpx.Response(412, json={}),
    )
    with pytest.raises(HingeAuthError):
        await client.submit_otp("000000")


async def test_submit_otp_http_error(client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/auth/sms/v2").mock(
        return_value=httpx.Response(401, json={}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.submit_otp("000000")


# --------------------------------------------------------------------------- #
# submit_email_code
# --------------------------------------------------------------------------- #


async def test_submit_email_code_success(client, base_url, respx_mock):
    expires = _iso(90)
    respx_mock.post(f"{base_url}/auth/device/validate").mock(
        return_value=httpx.Response(
            200,
            json={"identityId": "id-2", "token": "tok-2", "expires": expires},
        ),
    )
    client._pending_email_2fa = {"case_id": "c", "email": "e"}
    client._authenticate_with_sendbird = AsyncMock()
    await client.submit_email_code("999999", "case-1")
    assert client.hinge_token == "tok-2"
    assert client.identity_id == "id-2"
    assert client.auth_state == client.AUTH_AUTHENTICATED
    assert client._pending_email_2fa is None
    client._authenticate_with_sendbird.assert_awaited_once()


async def test_submit_email_code_http_error(client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/auth/device/validate").mock(
        return_value=httpx.Response(400, json={}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.submit_email_code("x", "y")


# --------------------------------------------------------------------------- #
# _authenticate_with_sendbird
# --------------------------------------------------------------------------- #


async def test_authenticate_with_sendbird_success(auth_client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/message/authenticate").mock(
        return_value=httpx.Response(200, json={"token": "sb-jwt", "expires": _iso(30)}),
    )
    fake_ws = _FakeWS("LOGI" + json.dumps({"key": "sess-key-1"}))
    with patch("websockets.connect", Mock(return_value=fake_ws)):
        await auth_client._authenticate_with_sendbird()
    assert auth_client.sendbird_jwt == "sb-jwt"
    assert auth_client.sendbird_session_key == "sess-key-1"


async def test_authenticate_with_sendbird_non_logi(auth_client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/message/authenticate").mock(
        return_value=httpx.Response(200, json={"token": "sb-jwt", "expires": _iso(30)}),
    )
    fake_ws = _FakeWS("ERRO{}")
    with (
        patch("websockets.connect", Mock(return_value=fake_ws)),
        pytest.raises(HingeAuthError),
    ):
        await auth_client._authenticate_with_sendbird()


async def test_authenticate_with_sendbird_no_websockets(
    auth_client,
    base_url,
    respx_mock,
):
    respx_mock.post(f"{base_url}/message/authenticate").mock(
        return_value=httpx.Response(200, json={"token": "sb-jwt", "expires": _iso(30)}),
    )
    # Setting the module to None makes ``import websockets`` raise ImportError.
    with patch.dict(sys.modules, {"websockets": None}):
        await auth_client._authenticate_with_sendbird()
    assert auth_client.sendbird_jwt == "sb-jwt"
    assert auth_client.sendbird_session_key == ""


async def test_authenticate_with_sendbird_http_error(auth_client, base_url, respx_mock):
    respx_mock.post(f"{base_url}/message/authenticate").mock(
        return_value=httpx.Response(500, json={}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client._authenticate_with_sendbird()


# --------------------------------------------------------------------------- #
# check_session_health
# --------------------------------------------------------------------------- #


async def test_check_session_health_no_token(client):
    assert await client.check_session_health() is None


async def test_check_session_health_success(auth_client, base_url, respx_mock):
    respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(200, json={"likesLeft": 10, "superlikesLeft": 2}),
    )
    limit = await auth_client.check_session_health()
    assert limit is not None
    assert limit.likes_left == 10
    assert limit.super_likes_left == 2


async def test_check_session_health_retry_then_success(
    auth_client,
    base_url,
    respx_mock,
):
    respx_mock.get(f"{base_url}/likelimit").mock(
        side_effect=[
            httpx.Response(401),
            httpx.Response(200, json={"likesLeft": 1, "superlikesLeft": 0}),
        ],
    )
    with patch("asyncio.sleep", AsyncMock()) as sleep:
        limit = await auth_client.check_session_health()
    assert limit is not None
    assert limit.likes_left == 1
    sleep.assert_awaited_once()


async def test_check_session_health_two_401_dead(auth_client, base_url, respx_mock):
    respx_mock.get(f"{base_url}/likelimit").mock(
        side_effect=[httpx.Response(401), httpx.Response(401)],
    )
    with patch("asyncio.sleep", AsyncMock()):
        result = await auth_client.check_session_health()
    assert result is None
    assert auth_client.auth_state == auth_client.AUTH_UNAUTHENTICATED


async def test_check_session_health_non_401_reraises(auth_client, base_url, respx_mock):
    respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(500),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.check_session_health()


# --------------------------------------------------------------------------- #
# is_session_valid
# --------------------------------------------------------------------------- #


async def test_is_session_valid_no_token(client):
    assert await client.is_session_valid() is False


async def test_is_session_valid_true(auth_client, base_url, respx_mock):
    respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(200, json={"likesLeft": 5, "superlikesLeft": 1}),
    )
    assert await auth_client.is_session_valid() is True


async def test_is_session_valid_health_none(auth_client, base_url, respx_mock):
    respx_mock.get(f"{base_url}/likelimit").mock(
        side_effect=[httpx.Response(401), httpx.Response(401)],
    )
    with patch("asyncio.sleep", AsyncMock()):
        assert await auth_client.is_session_valid() is False


async def test_is_session_valid_sendbird_reauth(auth_client, base_url, respx_mock):
    auth_client.sendbird_jwt = "old-jwt"
    auth_client.sendbird_jwt_expires = datetime.now(timezone.utc) - timedelta(days=1)
    respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(200, json={"likesLeft": 5, "superlikesLeft": 1}),
    )
    auth_client._authenticate_with_sendbird = AsyncMock()
    assert await auth_client.is_session_valid() is True
    auth_client._authenticate_with_sendbird.assert_awaited_once()


async def test_is_session_valid_no_sendbird_jwt(auth_client, base_url, respx_mock):
    auth_client.sendbird_jwt = ""
    auth_client.sendbird_jwt_expires = None
    respx_mock.get(f"{base_url}/likelimit").mock(
        return_value=httpx.Response(200, json={"likesLeft": 5, "superlikesLeft": 1}),
    )
    auth_client._authenticate_with_sendbird = AsyncMock()
    assert await auth_client.is_session_valid() is True
    auth_client._authenticate_with_sendbird.assert_not_awaited()


# --------------------------------------------------------------------------- #
# _derive_auth_state
# --------------------------------------------------------------------------- #


def test_derive_auth_state_pending_otp():
    assert client_core._derive_auth_state("pending_otp", "", "") == "pending_otp"


def test_derive_auth_state_pending_email():
    assert client_core._derive_auth_state("pending_email", "", "") == "pending_email"


def test_derive_auth_state_authenticated():
    assert (
        client_core._derive_auth_state("authenticated", "tok", _iso(1))
        == "authenticated"
    )


def test_derive_auth_state_expired():
    assert client_core._derive_auth_state("authenticated", "tok", _iso(-1)) == "expired"


def test_derive_auth_state_invalid_expires():
    assert (
        client_core._derive_auth_state("authenticated", "tok", "not-a-date")
        == "unauthenticated"
    )


def test_derive_auth_state_no_token():
    assert (
        client_core._derive_auth_state("authenticated", "", None) == "unauthenticated"
    )


def test_derive_auth_state_token_without_expires():
    assert (
        client_core._derive_auth_state("authenticated", "tok", None)
        == "unauthenticated"
    )


# --------------------------------------------------------------------------- #
# _preflight_refresh_session
# --------------------------------------------------------------------------- #


async def test_preflight_skip_no_token(tmp_path):
    now = datetime.now(timezone.utc)
    result = await client_core._preflight_refresh_session(
        {"auth_state": "authenticated", "phone_number": "+1"},
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "skipped"


async def test_preflight_skip_bad_state(tmp_path):
    now = datetime.now(timezone.utc)
    result = await client_core._preflight_refresh_session(
        {"hinge_token": "t", "auth_state": "pending_otp"},
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "skipped"


async def test_preflight_skip_expires_not_str(tmp_path):
    now = datetime.now(timezone.utc)
    result = await client_core._preflight_refresh_session(
        {
            "hinge_token": "t",
            "auth_state": "authenticated",
            "hinge_token_expires": None,
        },
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "skipped"


async def test_preflight_skip_expires_unparseable(tmp_path):
    now = datetime.now(timezone.utc)
    result = await client_core._preflight_refresh_session(
        {
            "hinge_token": "t",
            "auth_state": "authenticated",
            "hinge_token_expires": "garbage",
        },
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "skipped"


async def test_preflight_expired(tmp_path):
    now = datetime.now(timezone.utc)
    expires = (now - timedelta(days=1)).isoformat()
    result = await client_core._preflight_refresh_session(
        {
            "hinge_token": "t",
            "auth_state": "authenticated",
            "hinge_token_expires": expires,
        },
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "expired"


async def test_preflight_skip_not_expiring_soon(tmp_path):
    # No auth_state key -> defaults to "" which passes the guard; exercises the
    # ``expires > threshold`` skip branch.
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=30)).isoformat()
    result = await client_core._preflight_refresh_session(
        {"hinge_token": "t", "hinge_token_expires": expires},
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "skipped"


async def test_preflight_refresh_success(tmp_path, base_url, respx_mock):
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=7)).isoformat()
    new_expires = (now + timedelta(days=90)).isoformat()
    route = respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(
            201,
            json={"token": "new", "identityId": "nid", "expires": new_expires},
        ),
    )
    fpath = tmp_path / "s.json"
    data = {
        "hinge_token": "old",
        "auth_state": "authenticated",
        "hinge_token_expires": expires,
        "phone_number": "+1",
    }
    result = await client_core._preflight_refresh_session(
        data,
        str(fpath),
        now,
        now + timedelta(days=14),
    )
    assert route.called
    assert result == "refreshed"
    assert data["hinge_token"] == "new"
    assert data["identity_id"] == "nid"
    assert data["hinge_token_expires"] == new_expires
    written = json.loads(fpath.read_text("utf-8"))
    assert written["hinge_token"] == "new"


async def test_preflight_refresh_failed_non_201(tmp_path, base_url, respx_mock):
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=7)).isoformat()
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(400, json={}),
    )
    data = {
        "hinge_token": "old",
        "auth_state": "authenticated",
        "hinge_token_expires": expires,
    }
    result = await client_core._preflight_refresh_session(
        data,
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "failed"
    assert data["hinge_token"] == "old"


async def test_preflight_refresh_exception(tmp_path, base_url, respx_mock):
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=7)).isoformat()
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        side_effect=httpx.ConnectError("boom"),
    )
    data = {
        "hinge_token": "old",
        "auth_state": "authenticated",
        "hinge_token_expires": expires,
    }
    result = await client_core._preflight_refresh_session(
        data,
        str(tmp_path / "s.json"),
        now,
        now + timedelta(days=14),
    )
    assert result == "failed"
