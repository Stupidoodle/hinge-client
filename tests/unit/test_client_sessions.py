"""Unit tests for HingeClient session persistence (client/_core.py).

Covers session file path derivation, load/create/migrate/auto-detect logic,
auth-state application, save/skip behaviour, the recommendation cache
round-trip, and the session-management static methods (list_sessions,
switch_session, refresh_all_sessions).

Everything is offline: HTTP is mocked with respx and the session store is
redirected to an isolated temp dir by the ``sessions_dir`` fixture.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import httpx

import hinge.client._core as client_core
from hinge.client import BASE_URL, HingeClient
from hinge.client._core import _derive_auth_state
from hinge.models import RecommendationSubject


# --- helpers ---------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _future_iso(days: int = 90) -> str:
    return (_now() + timedelta(days=days)).isoformat()


def _past_iso(days: int = 1) -> str:
    return (_now() - timedelta(days=days)).isoformat()


def _payload(**overrides: object) -> dict[str, object]:
    """Build a canonical session-data dict, overriding any field."""
    data: dict[str, object] = {
        "phone_number": "+15555550000",
        "device_id": "DEVICE-ID",
        "installed": True,
        "install_id": "INSTALL-ID",
        "session_id": "SESSION-ID",
        "hinge_token": "tok",
        "hinge_token_expires": _future_iso(),
        "identity_id": "identity-abc",
        "sendbird_jwt": "sb-jwt",
        "sendbird_session_key": "sb-key",
        "sendbird_jwt_expires": _future_iso(),
        "auth_state": "authenticated",
    }
    data.update(overrides)
    return data


def _write(directory, name: str, payload: dict[str, object]) -> None:
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


# --- _session_file_for -----------------------------------------------------


def test_session_file_for_strips_spaces_and_dashes_keeps_plus(sessions_dir):
    path = HingeClient._session_file_for("+1 555-0100")
    assert os.path.basename(path) == "+15550100.json"
    assert os.path.dirname(path) == str(sessions_dir)


def test_session_file_for_no_plus(sessions_dir):
    path = HingeClient._session_file_for("15555550100")
    assert os.path.basename(path) == "15555550100.json"


# --- _candidate_session_paths ----------------------------------------------


def test_candidate_paths_plus_phone_yields_canonical_and_legacy(client):
    paths = client._candidate_session_paths()
    assert len(paths) == 2
    assert os.path.basename(paths[0]) == "+15555550100.json"
    assert os.path.basename(paths[1]) == "15555550100.json"


def test_candidate_paths_no_plus_phone_collapses_to_one(sessions_dir):
    c = HingeClient("15555550160")
    paths = c._candidate_session_paths()
    assert len(paths) == 1
    assert os.path.basename(paths[0]) == "15555550160.json"


# --- _load_or_create_session ----------------------------------------------


def test_load_canonical_session(sessions_dir):
    _write(
        sessions_dir,
        "+15555550120.json",
        _payload(phone_number="+15555550120", identity_id="canon-id"),
    )
    c = HingeClient("+15555550120")
    assert c.auth_state == HingeClient.AUTH_AUTHENTICATED
    assert c.identity_id == "canon-id"
    # No migration: canonical file remains.
    assert os.path.exists(sessions_dir / "+15555550120.json")


def test_load_legacy_session_migrates_and_removes_old(sessions_dir):
    _write(
        sessions_dir,
        "15555550150.json",  # legacy: no leading +
        _payload(phone_number="+15555550150", identity_id="legacy-id"),
    )
    c = HingeClient("+15555550150")
    assert c.identity_id == "legacy-id"
    assert c.auth_state == HingeClient.AUTH_AUTHENTICATED
    # Migrated to canonical, legacy removed.
    assert os.path.exists(sessions_dir / "+15555550150.json")
    assert not os.path.exists(sessions_dir / "15555550150.json")


def test_corrupt_canonical_falls_through_to_create(sessions_dir):
    (sessions_dir / "+15555550199.json").write_text("{ not json", encoding="utf-8")
    c = HingeClient("+15555550199")
    # Corrupt file ignored, fresh session created and written over it.
    assert c.auth_state == HingeClient.AUTH_UNAUTHENTICATED
    assert c.hinge_token == ""
    restored = json.loads((sessions_dir / "+15555550199.json").read_text("utf-8"))
    assert restored["auth_state"] == "unauthenticated"


def test_no_phone_auto_detects_authenticated_session(sessions_dir):
    # Files exercised in sorted order: non-json -> corrupt -> unauth -> good.
    (sessions_dir / "a_skip.txt").write_text("ignored", encoding="utf-8")
    (sessions_dir / "aaa_corrupt.json").write_text("nope", encoding="utf-8")
    _write(
        sessions_dir,
        "bbb_unauth.json",
        _payload(phone_number="+15555551111", auth_state="unauthenticated"),
    )
    _write(
        sessions_dir,
        "ccc_good.json",
        _payload(phone_number="+15555559999", identity_id="auto-id"),
    )

    c = HingeClient("")
    assert c.phone_number == "+15555559999"
    assert c.identity_id == "auto-id"
    assert c.auth_state == HingeClient.AUTH_AUTHENTICATED
    assert c.session_file == str(sessions_dir / "ccc_good.json")


def test_no_phone_no_session_creates_fresh(sessions_dir):
    c = HingeClient("")
    assert c.auth_state == HingeClient.AUTH_UNAUTHENTICATED
    assert c.hinge_token == ""


# --- _apply_session_data ---------------------------------------------------


def test_apply_authenticated_valid(client):
    client._apply_session_data(_payload(identity_id="id-1"))
    assert client.auth_state == HingeClient.AUTH_AUTHENTICATED
    assert client.hinge_token == "tok"
    assert client.identity_id == "id-1"
    assert client.sendbird_jwt == "sb-jwt"
    assert client.sendbird_session_key == "sb-key"
    assert client.installed is True


def test_apply_authenticated_but_expired_downgrades(client):
    client._apply_session_data(
        _payload(auth_state="authenticated", hinge_token_expires=_past_iso()),
    )
    assert client.auth_state == HingeClient.AUTH_UNAUTHENTICATED


def test_apply_authenticated_but_no_token_downgrades(client):
    client._apply_session_data(
        _payload(auth_state="authenticated", hinge_token=""),
    )
    assert client.auth_state == HingeClient.AUTH_UNAUTHENTICATED


def test_apply_pending_otp_preserved(client):
    client._apply_session_data(_payload(auth_state="pending_otp", hinge_token=""))
    assert client.auth_state == HingeClient.AUTH_PENDING_OTP


def test_apply_pending_email_preserved(client):
    client._apply_session_data(_payload(auth_state="pending_email", hinge_token=""))
    assert client.auth_state == HingeClient.AUTH_PENDING_EMAIL


def test_apply_unauthenticated_preserved(client):
    client._apply_session_data(_payload(auth_state="unauthenticated"))
    assert client.auth_state == HingeClient.AUTH_UNAUTHENTICATED


def test_apply_unknown_state_with_valid_token_derives_authenticated(client):
    data = _payload()
    del data["auth_state"]
    client._apply_session_data(data)
    assert client.auth_state == HingeClient.AUTH_AUTHENTICATED


def test_apply_unknown_state_without_token_derives_unauthenticated(client):
    client._apply_session_data(_payload(auth_state="weird", hinge_token=""))
    assert client.auth_state == HingeClient.AUTH_UNAUTHENTICATED


def test_apply_empty_data_uses_defaults(client):
    client._apply_session_data({})
    assert len(client.device_id) == 36
    assert "-" in client.device_id
    assert client.installed is False
    assert client.hinge_token == ""
    assert client.auth_state == HingeClient.AUTH_UNAUTHENTICATED
    # Missing expiry fields default to ~now.
    assert abs((_now() - client.hinge_token_expires).total_seconds()) < 5
    assert abs((_now() - client.sendbird_jwt_expires).total_seconds()) < 5


# --- _create_session -------------------------------------------------------


def test_create_session_generates_fresh_uuids(sessions_dir):
    c = HingeClient("+15555550140")
    assert c.auth_state == HingeClient.AUTH_UNAUTHENTICATED
    assert c.installed is False
    assert len(c.device_id) == 36
    assert len(c.install_id) == 36
    assert len(c.session_id) == 36
    assert c.device_id != c.install_id != c.session_id


# --- _save_session ---------------------------------------------------------


def test_save_session_skips_when_no_phone(client, tmp_path):
    target = tmp_path / "should-not-exist.json"
    client.session_file = str(target)
    client.phone_number = ""
    client._save_session()
    assert not target.exists()


def test_save_session_skips_when_whitespace_phone(client, tmp_path):
    target = tmp_path / "should-not-exist.json"
    client.session_file = str(target)
    client.phone_number = "   "
    client._save_session()
    assert not target.exists()


def test_save_session_writes_all_fields(client):
    client.hinge_token = "saved-tok"
    client.identity_id = "saved-id"
    client.auth_state = HingeClient.AUTH_AUTHENTICATED
    client._save_session()
    data = json.loads(open(client.session_file).read())
    assert data["phone_number"] == "+15555550100"
    assert data["hinge_token"] == "saved-tok"
    assert data["identity_id"] == "saved-id"
    assert data["auth_state"] == "authenticated"
    assert data["hinge_token_expires"] == client.hinge_token_expires.isoformat()
    assert data["sendbird_jwt_expires"] == client.sendbird_jwt_expires.isoformat()


# --- recommendation cache round-trip --------------------------------------


def test_recommendations_round_trip(client, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    subject = RecommendationSubject(
        subject_id="sub-1",
        rating_token="rt-1",
        origin="compatibles",
    )
    client._rec_cache = {"sub-1": subject}
    client._save_recommendations()

    client._rec_cache = {}
    client._load_recommendations()
    assert "sub-1" in client._rec_cache
    assert client._rec_cache["sub-1"].rating_token == "rt-1"
    assert client._rec_cache["sub-1"].origin == "compatibles"


def test_load_recommendations_missing_file(client, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    client._rec_cache = {"stale": object()}
    client._load_recommendations()
    assert client._rec_cache == {}


def test_load_recommendations_corrupt_file(client, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / f"recommendations_{client.session_id}.json").write_text(
        "{ not json",
        encoding="utf-8",
    )
    client._load_recommendations()
    assert client._rec_cache == {}


# --- _derive_auth_state ----------------------------------------------------


def test_derive_pending_states_passthrough():
    assert _derive_auth_state("pending_otp", "", None) == "pending_otp"
    assert _derive_auth_state("pending_email", "", None) == "pending_email"


def test_derive_valid_token_authenticated():
    assert _derive_auth_state("", "tok", _future_iso()) == "authenticated"


def test_derive_expired_token():
    assert _derive_auth_state("", "tok", _past_iso()) == "expired"


def test_derive_unparseable_expiry_falls_back():
    assert _derive_auth_state("", "tok", "not-a-date") == "unauthenticated"


def test_derive_token_without_expiry():
    assert _derive_auth_state("", "tok", None) == "unauthenticated"


def test_derive_no_token():
    assert _derive_auth_state("", "", None) == "unauthenticated"


# --- list_sessions ---------------------------------------------------------


def test_list_sessions_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(client_core, "SESSIONS_DIR", str(tmp_path / "nope"))
    assert HingeClient.list_sessions() == []


def test_list_sessions_scans_and_classifies(sessions_dir):
    _write(
        sessions_dir,
        "auth.json",
        _payload(phone_number="+1A", identity_id="idA"),
    )
    _write(
        sessions_dir,
        "expired.json",
        _payload(phone_number="+1B", hinge_token_expires=_past_iso()),
    )
    _write(
        sessions_dir,
        "pending.json",
        _payload(phone_number="+1C", auth_state="pending_otp"),
    )
    _write(
        sessions_dir,
        "notoken.json",
        _payload(phone_number="+1D", hinge_token="", auth_state=""),
    )
    _write(
        sessions_dir,
        "baddate.json",
        _payload(phone_number="+1E", hinge_token_expires="garbage", auth_state=""),
    )
    (sessions_dir / "ignore.txt").write_text("x", encoding="utf-8")
    (sessions_dir / "corrupt.json").write_text("nope", encoding="utf-8")

    by_phone = {s["phone_number"]: s for s in HingeClient.list_sessions()}
    assert len(by_phone) == 5
    assert by_phone["+1A"]["auth_state"] == "authenticated"
    assert by_phone["+1A"]["needs_reauth"] is False
    assert by_phone["+1A"]["identity_id"] == "idA"
    assert by_phone["+1B"]["auth_state"] == "expired"
    assert by_phone["+1B"]["needs_reauth"] is True
    assert by_phone["+1C"]["auth_state"] == "pending_otp"
    assert by_phone["+1C"]["needs_reauth"] is False
    assert by_phone["+1D"]["auth_state"] == "unauthenticated"
    assert by_phone["+1D"]["needs_reauth"] is True
    assert by_phone["+1E"]["auth_state"] == "unauthenticated"
    assert by_phone["+1E"]["needs_reauth"] is True


# --- switch_session --------------------------------------------------------


def test_switch_session_loads_existing(auth_client, sessions_dir):
    _write(
        sessions_dir,
        "+15555550180.json",
        _payload(phone_number="+15555550180", identity_id="switched-id"),
    )
    auth_client.switch_session("+15555550180")
    assert auth_client.phone_number == "+15555550180"
    assert auth_client.identity_id == "switched-id"
    assert auth_client.auth_state == HingeClient.AUTH_AUTHENTICATED
    assert auth_client.session_file == str(sessions_dir / "+15555550180.json")


def test_switch_session_creates_new_when_absent(auth_client, sessions_dir):
    auth_client.switch_session("+15555550181")
    assert auth_client.phone_number == "+15555550181"
    assert auth_client.auth_state == HingeClient.AUTH_UNAUTHENTICATED
    assert auth_client.hinge_token == ""
    assert os.path.exists(sessions_dir / "+15555550181.json")


# --- refresh_all_sessions --------------------------------------------------


async def test_refresh_all_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(client_core, "SESSIONS_DIR", str(tmp_path / "nope"))
    assert await HingeClient.refresh_all_sessions() == {}


async def test_refresh_all_branches_without_http(sessions_dir):
    _write(
        sessions_dir,
        "p_future.json",
        _payload(phone_number="+1A", hinge_token_expires=_future_iso(365)),
    )
    _write(
        sessions_dir,
        "p_past.json",
        _payload(phone_number="+1B", hinge_token_expires=_past_iso()),
    )
    _write(
        sessions_dir,
        "p_notoken.json",
        _payload(phone_number="+1C", hinge_token=""),
    )
    _write(
        sessions_dir,
        "p_nonstr.json",
        _payload(phone_number="+1D", hinge_token_expires=12345),
    )
    _write(
        sessions_dir,
        "p_badexpires.json",
        _payload(phone_number="+1E", hinge_token_expires="not-a-date"),
    )
    _write(
        sessions_dir,
        "p_pending.json",
        _payload(phone_number="+1F", auth_state="pending_otp"),
    )
    nophone = _payload(hinge_token_expires=_future_iso(365))
    del nophone["phone_number"]
    _write(sessions_dir, "p_nophone.json", nophone)
    (sessions_dir / "corrupt.json").write_text("nope", encoding="utf-8")
    (sessions_dir / "ignore.txt").write_text("x", encoding="utf-8")

    results = await HingeClient.refresh_all_sessions()
    assert results["+1A"] == "skipped"
    assert results["+1B"] == "expired"
    assert results["+1C"] == "skipped"
    assert results["+1D"] == "skipped"
    assert results["+1E"] == "skipped"
    assert results["+1F"] == "skipped"
    assert results["p_nophone.json"] == "skipped"
    assert "corrupt" not in str(results)
    assert len(results) == 7


async def test_refresh_all_refreshes_expiring_token(sessions_dir, respx_mock):
    _write(
        sessions_dir,
        "p_refresh.json",
        _payload(phone_number="+15555550170", hinge_token_expires=_future_iso(5)),
    )
    new_expiry = _future_iso(120)
    respx_mock.get(f"{BASE_URL}/auth/refresh").respond(
        status_code=201,
        json={"token": "new-tok", "identityId": "new-id", "expires": new_expiry},
    )

    results = await HingeClient.refresh_all_sessions(threshold_days=14)
    assert results["+15555550170"] == "refreshed"
    saved = json.loads((sessions_dir / "p_refresh.json").read_text("utf-8"))
    assert saved["hinge_token"] == "new-tok"
    assert saved["identity_id"] == "new-id"
    assert saved["hinge_token_expires"] == new_expiry


async def test_refresh_all_non_201_is_failed(sessions_dir, respx_mock):
    _write(
        sessions_dir,
        "p_refresh.json",
        _payload(phone_number="+15555550171", hinge_token_expires=_future_iso(5)),
    )
    respx_mock.get(f"{BASE_URL}/auth/refresh").respond(status_code=500)
    results = await HingeClient.refresh_all_sessions(threshold_days=14)
    assert results["+15555550171"] == "failed"


async def test_refresh_all_request_error_is_failed(sessions_dir, respx_mock):
    _write(
        sessions_dir,
        "p_refresh.json",
        _payload(phone_number="+15555550172", hinge_token_expires=_future_iso(5)),
    )
    respx_mock.get(f"{BASE_URL}/auth/refresh").mock(
        side_effect=httpx.ConnectError("boom"),
    )
    results = await HingeClient.refresh_all_sessions(threshold_days=14)
    assert results["+15555550172"] == "failed"
