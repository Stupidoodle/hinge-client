"""Live integration scaffolds for the Hinge client.

These tests are gated twice over:

* the ``integration`` marker (``pytest -m integration`` to select them), and
* the presence of real credentials in the environment.

Under the default offline test suite they are collected but **skipped
immediately** — they perform NO network I/O, touch NO real credentials, and
require explicit opt-in via environment variables:

==================  =========================================================
``HINGE_TEST_PHONE``  E.164 phone number of a real Hinge account (gates all)
``HINGE_TEST_OTP``    SMS OTP code, only for the live login scaffold
==================  =========================================================

Run them explicitly, e.g.::

    HINGE_TEST_PHONE=+15555550123 HINGE_TEST_OTP=123456 \
        uv run pytest tests/integration -m integration

Because the skip is decided by ``skipif`` (and a guard inside the login
scaffold), the bodies below never execute in the default suite, so no socket
is ever opened and no session file is ever read.
"""

import os

import pytest

from hinge import HingeClient
from hinge.models import RecommendationsResponse

# Credentials that gate the live tests. Absent in CI / the default run, so the
# ``skipif`` below short-circuits every test before any client is constructed.
_PHONE = os.environ.get("HINGE_TEST_PHONE")
_OTP = os.environ.get("HINGE_TEST_OTP")

requires_credentials = pytest.mark.skipif(
    not _PHONE,
    reason="set HINGE_TEST_PHONE (+HINGE_TEST_OTP) to run live integration tests",
)


@pytest.mark.integration
@requires_credentials
async def test_live_login_flow():
    """Full SMS-OTP login against the real Hinge identity service."""
    if not _OTP:
        pytest.skip("set HINGE_TEST_OTP to run the live login scaffold")
    assert _PHONE is not None  # narrowed by the skipif gate

    client = HingeClient(_PHONE)
    await client.initiate_login()
    assert client.auth_state == client.AUTH_PENDING_OTP

    await client.submit_otp(_OTP)
    assert client.auth_state == client.AUTH_AUTHENTICATED
    assert client.hinge_token
    assert await client.is_session_valid()


@pytest.mark.integration
@requires_credentials
async def test_live_recommendations_feed():
    """Fetch the live recommendation feed for a stored, valid session."""
    assert _PHONE is not None  # narrowed by the skipif gate

    client = HingeClient(_PHONE)
    if not await client.is_session_valid():
        pytest.skip("no valid stored session for HINGE_TEST_PHONE; log in first")

    feed = await client.recommendations.list()
    assert isinstance(feed, RecommendationsResponse)
