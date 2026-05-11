"""Hinge API dependency injection."""

from datetime import datetime, timezone

from hinge.core.logging_config import logger as log
from hinge.bootstrap import HingeContainer
from hinge.client import HingeClient
from hinge.error import HingeSessionExpiredError

_container: HingeContainer | None = None


def set_hinge_container(container: HingeContainer) -> None:
    """Set the global Hinge container (called at startup)."""
    global _container  # noqa: PLW0603
    _container = container


def get_hinge_container() -> HingeContainer:
    """Get the global Hinge container for dependency injection."""
    if _container is None:
        raise RuntimeError("Hinge container not initialized")
    return _container


def _is_authenticated(client: HingeClient) -> bool:
    return (
        client.auth_state == HingeClient.AUTH_AUTHENTICATED
        and bool(client.hinge_token)
        and client.hinge_token_expires > datetime.now(timezone.utc)
    )


async def require_hinge_auth() -> HingeContainer:
    """Gate on local auth state — fast path, no upstream call.

    If in-memory state is unauthenticated, reloads the session file
    in case it was updated externally (e.g. re-auth in another process).
    Proactively refreshes the token if it expires within 7 days.
    """
    container = get_hinge_container()
    client = container._client

    # Proactive refresh before checking — avoids unnecessary 401s
    if client.auth_state == HingeClient.AUTH_AUTHENTICATED and client.hinge_token:
        await client.ensure_fresh_token()

    if not _is_authenticated(client):
        # Reload session from disk — file may have been updated externally
        client._load_or_create_session()
        if _is_authenticated(client):
            log.info("session_reloaded_from_disk")
        else:
            raise HingeSessionExpiredError

    return container
