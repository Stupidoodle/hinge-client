"""Shared pytest fixtures for the hinge client test suite.

HTTP is mocked with ``respx`` (its ``respx_mock`` fixture is available in any
test). Sessions are isolated to a temp dir so tests never touch the real store.
No network, no real credentials — anything hitting the live API belongs in
``tests/integration`` behind ``@pytest.mark.integration``.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

import hinge.client._core as client_core
from hinge.client import BASE_URL, HingeClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Load a JSON fixture by filename (relative to ``tests/fixtures``)."""
    return json.loads((FIXTURES / name).read_text("utf-8"))


@pytest.fixture
def base_url() -> str:
    """Hinge API base URL, for registering respx routes."""
    return BASE_URL


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Redirect the per-phone session store to an isolated temp dir."""
    d = tmp_path / "sessions"
    d.mkdir()
    monkeypatch.setattr(client_core, "SESSIONS_DIR", str(d))
    return d


@pytest.fixture
def client(sessions_dir):
    """A fresh, unauthenticated client with an isolated session dir."""
    return HingeClient("+15555550100")


@pytest.fixture
def auth_client(sessions_dir):
    """An authenticated client with a far-future Hinge + Sendbird token."""
    c = HingeClient("+15555550101")
    future = datetime.now(timezone.utc) + timedelta(days=90)
    c.hinge_token = "test-hinge-token"
    c.identity_id = "test-identity-id"
    c.auth_state = c.AUTH_AUTHENTICATED
    c.hinge_token_expires = future
    c.sendbird_jwt = "test-sendbird-jwt"
    c.sendbird_session_key = "test-sendbird-session-key"
    c.sendbird_jwt_expires = future
    return c
