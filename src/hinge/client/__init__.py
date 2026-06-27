"""Async client for the Hinge API.

Exposes :class:`HingeClient` plus the top-level constants kept here for
backwards-compatible imports (``from hinge.client import BASE_URL``).
"""

from hinge.client._core import (
    BASE_URL as BASE_URL,
    SENDBIRD_APP_ID as SENDBIRD_APP_ID,
    SESSIONS_DIR as SESSIONS_DIR,
    HingeClient,
)

__all__ = ["HingeClient"]
