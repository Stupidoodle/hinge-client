"""Repo-wide secret-hygiene guards.

Two independent guards live here:

1. LEAK-CANARY — a ``git grep`` over *tracked* files must never surface the
   reverse-engineering toolchain vocabulary (decompilers, smali, the rival app,
   obfuscated package fragments, ...). The ``.gitignore`` legitimately mentions
   some of these words (it is what keeps the toolchain out of the tree) and this
   very test file spells them out, so both are excluded from the search.

2. TOKENS-NEVER-LOGGED — refreshing the Hinge token must rotate the secret
   without ever emitting the old or new token (or the Sendbird credentials) into
   the log stream, at any log level.
"""

import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import structlog
from structlog.testing import capture_logs

from hinge.core.logging import configure_logging

REPO_ROOT = Path(__file__).resolve().parents[1]

# The forbidden vocabulary. Mirrors the orchestrator's canary pattern.
CANARY_PATTERN = (
    r"bumble|decompil|jadx|smali|dk8|qoh|defpackage|moshi|"
    r"jsonadapter|hinge-decompiled|\bapk\b"
)

# Synthetic, obviously-fake secrets — never anything real.
OLD_HINGE_TOKEN = "OLD-SECRET-hinge-tok-1111aaaa"
NEW_HINGE_TOKEN = "NEW-SECRET-hinge-tok-2222bbbb"
SENDBIRD_JWT = "SECRET-sendbird-jwt-3333cccc"
SENDBIRD_KEY = "SECRET-sendbird-key-4444dddd"

ALL_SECRETS = (OLD_HINGE_TOKEN, NEW_HINGE_TOKEN, SENDBIRD_JWT, SENDBIRD_KEY)


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Restore structlog's lazy default config after each logging test.

    ``configure_logging`` mutates structlog's global state; leaving it
    configured would pollute unrelated test modules.
    """
    yield
    structlog.reset_defaults()


# --------------------------------------------------------------------------- #
# 1. LEAK-CANARY
# --------------------------------------------------------------------------- #


def test_no_reversing_vocab_in_tracked_files():
    """No tracked file (sans .gitignore / this file) leaks toolchain words."""
    proc = subprocess.run(
        [
            "git",
            "grep",
            "-niE",
            CANARY_PATTERN,
            "--",
            ":(exclude).gitignore",
            ":(exclude)tests/test_no_secrets.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    # git grep: 0 == matches found (bad), 1 == clean, >1 == invocation error.
    assert proc.returncode != 0, (
        f"Leak-canary matched forbidden vocabulary in tracked files:\n{proc.stdout}"
    )
    assert proc.returncode == 1, (
        f"git grep failed to run (exit {proc.returncode}):\n{proc.stderr}"
    )
    assert proc.stdout == ""


@pytest.mark.parametrize(
    "planted",
    [
        "this line mentions jadx",
        "an apk file lives here",
        "Bumble does it differently",
        "see the smali output",
        "decompiled with care",
        "a Moshi JsonAdapter",
    ],
)
def test_leak_canary_pattern_actually_matches(planted):
    """Sanity: the canary regex *does* catch planted vocabulary.

    Guards against a silently-broken regex turning the real guard into a
    vacuous pass. The case-insensitive search mirrors ``git grep -niE``.
    """
    assert re.search(CANARY_PATTERN, planted, re.IGNORECASE) is not None


def test_leak_canary_pattern_has_word_boundary_on_apk():
    """``\\bapk\\b`` matches the standalone word but not substrings."""
    assert re.search(CANARY_PATTERN, "an apk", re.IGNORECASE) is not None
    assert re.search(CANARY_PATTERN, "knapkin sapkow", re.IGNORECASE) is None


# --------------------------------------------------------------------------- #
# 2. TOKENS-NEVER-LOGGED
# --------------------------------------------------------------------------- #


def _arm_refresh_secrets(client):
    """Plant fake secrets and make the Hinge token expire within the window."""
    client.hinge_token = OLD_HINGE_TOKEN
    client.sendbird_jwt = SENDBIRD_JWT
    client.sendbird_session_key = SENDBIRD_KEY
    client.auth_state = client.AUTH_AUTHENTICATED
    # Inside the 7-day proactive-refresh window so the refresh branch runs.
    client.hinge_token_expires = datetime.now(timezone.utc) + timedelta(days=2)


def _assert_no_secrets(blob: str) -> None:
    for secret in ALL_SECRETS:
        assert secret not in blob, f"secret leaked into logs: {secret!r}\n{blob}"


async def test_refresh_success_capsys(auth_client, respx_mock, base_url, capsys):
    """Rendered log output of a successful refresh contains no secrets."""
    _arm_refresh_secrets(auth_client)
    new_expires = (datetime.now(timezone.utc) + timedelta(days=120)).isoformat()
    route = respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(
            201,
            json={
                "token": NEW_HINGE_TOKEN,
                "identityId": "new-identity-id",
                "expires": new_expires,
            },
        ),
    )

    configure_logging(level="DEBUG", pretty=False)
    await auth_client.ensure_fresh_token()

    assert route.called
    assert auth_client.hinge_token == NEW_HINGE_TOKEN

    captured = capsys.readouterr().err
    # Logging actually happened (test is not vacuous) ...
    assert "hinge_token_refresh_starting" in captured
    assert "hinge_token_refreshed" in captured
    # ... but no secret made it into the stream.
    _assert_no_secrets(captured)


async def test_refresh_failure_never_logs_tokens(
    auth_client, respx_mock, base_url, capsys
):
    """A non-201 refresh logs a warning (with body) but never the stored token."""
    _arm_refresh_secrets(auth_client)
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(500, text="upstream exploded, no creds here"),
    )

    configure_logging(level="DEBUG", pretty=False)
    await auth_client.ensure_fresh_token()

    # Failure path leaves the existing token untouched.
    assert auth_client.hinge_token == OLD_HINGE_TOKEN

    captured = capsys.readouterr().err
    assert "hinge_token_refresh_failed" in captured
    _assert_no_secrets(captured)


async def test_refresh_transport_error_never_logs_tokens(
    auth_client, respx_mock, base_url, capsys
):
    """An exception during refresh is logged with a traceback, sans secrets."""
    _arm_refresh_secrets(auth_client)
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        side_effect=httpx.ConnectError("connection refused"),
    )

    configure_logging(level="DEBUG", pretty=False)
    await auth_client.ensure_fresh_token()

    assert auth_client.hinge_token == OLD_HINGE_TOKEN

    captured = capsys.readouterr().err
    assert "hinge_token_refresh_error" in captured
    _assert_no_secrets(captured)


async def test_refresh_structlog_event_dicts_carry_no_tokens(
    auth_client, respx_mock, base_url
):
    """The structured event dicts themselves never carry a secret value."""
    _arm_refresh_secrets(auth_client)
    new_expires = (datetime.now(timezone.utc) + timedelta(days=120)).isoformat()
    respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(
            201,
            json={
                "token": NEW_HINGE_TOKEN,
                "identityId": "new-identity-id",
                "expires": new_expires,
            },
        ),
    )

    with capture_logs() as logs:
        await auth_client.ensure_fresh_token()

    assert auth_client.hinge_token == NEW_HINGE_TOKEN
    assert logs, "expected at least one structured log event"
    blob = repr(logs)
    _assert_no_secrets(blob)


async def test_no_refresh_no_logs_when_token_fresh(
    auth_client, respx_mock, base_url, capsys
):
    """A far-future token short-circuits: no refresh request, no refresh logs."""
    auth_client.hinge_token = OLD_HINGE_TOKEN
    auth_client.auth_state = auth_client.AUTH_AUTHENTICATED
    auth_client.hinge_token_expires = datetime.now(timezone.utc) + timedelta(days=90)
    route = respx_mock.get(f"{base_url}/auth/refresh").mock(
        return_value=httpx.Response(201, json={"token": NEW_HINGE_TOKEN}),
    )

    configure_logging(level="DEBUG", pretty=False)
    await auth_client.ensure_fresh_token()

    assert not route.called
    assert auth_client.hinge_token == OLD_HINGE_TOKEN
    captured = capsys.readouterr().err
    assert "hinge_token_refresh" not in captured
    _assert_no_secrets(captured)
