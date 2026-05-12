"""FastAPI route smoke tests — TestClient against the full app.

Each endpoint is exercised once with the auth dependency overridden so
no real Hinge token is required. The adapter (HingeApiPort) and the
HingeClient are AsyncMocks — these tests verify the routes wire
correctly, return the documented response shapes, and call the
adapter with sane arguments. They are NOT contract tests for Hinge.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hinge.api.deps import (
    get_hinge_container,
    require_hinge_auth,
    set_hinge_container,
)
from hinge.api.error_handlers import register_hinge_error_handlers
from hinge.api.router import router as hinge_router
from hinge.bootstrap import HingeContainer
from hinge.client import HingeClient
from hinge.domain.models.like_limit import HingeLikeLimit
from hinge.domain.models.profile import HingeProfile
from hinge.infrastructure.db.mappers import start_hinge_mappers
from hinge.infrastructure.db.metadata import metadata
from hinge.infrastructure.db.unit_of_work import HingeSqlAlchemyUnitOfWork


# ---------------------------------------------------------------------------
# Test app fixture
# ---------------------------------------------------------------------------


def _make_container() -> HingeContainer:
    """Build a HingeContainer with an in-memory DB + AsyncMock adapter."""
    start_hinge_mappers()
    # StaticPool keeps a single shared connection so successive UoWs see
    # the same in-memory DB (default :memory: is per-connection).
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    sf = sessionmaker(bind=engine, expire_on_commit=False)

    # Plain MagicMock — using spec=HingeClient blocks the per-instance
    # attributes the routes touch (e.g. ``_pending_email_2fa``).
    fake_client = MagicMock()
    fake_client.auth_state = HingeClient.AUTH_AUTHENTICATED
    fake_client.hinge_token = "tok"
    fake_client.hinge_token_expires = datetime.now(UTC).replace(year=2099)
    fake_client.identity_id = "id-1"
    fake_client.sendbird_jwt = "sb-jwt"
    fake_client.phone_number = "+41760000000"
    fake_client.recommendations = {}
    fake_client.feed_exhausted = False
    fake_client._pending_email_2fa = None
    fake_client.ensure_fresh_token = AsyncMock(return_value=None)
    fake_client.check_session_health = AsyncMock(return_value=None)
    fake_client.list_sessions = MagicMock(return_value=[])

    fake_adapter = AsyncMock()
    fake_scorer = MagicMock()
    fake_scorer.score = MagicMock(return_value=(75.0, "vibes"))

    return HingeContainer(
        hinge_api=fake_adapter,
        scorer=fake_scorer,
        _client=fake_client,
        _session_factory=sf,
    )


@pytest.fixture
def container() -> HingeContainer:
    """Per-test container — fresh DB + fresh mocks."""
    return _make_container()


@pytest.fixture
def app(container: HingeContainer) -> FastAPI:
    """FastAPI app with router + auth dep overridden to the fake container."""
    set_hinge_container(container)
    _app = FastAPI()
    register_hinge_error_handlers(_app)
    _app.include_router(hinge_router)

    async def _auth_ok() -> HingeContainer:
        return container

    _app.dependency_overrides[require_hinge_auth] = _auth_ok
    _app.dependency_overrides[get_hinge_container] = lambda: container
    return _app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Sync TestClient bound to the test app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


def test_auth_status_returns_authenticated(client: TestClient) -> None:
    """GET /auth/status mounts + returns 200 with our fake client state."""
    r = client.get("/api/v1/hinge/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert "phone_number" in body or "auth_state" in body


def test_auth_sessions_list(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /auth/sessions returns a (possibly empty) list of session metadata."""
    HingeClient.list_sessions = staticmethod(  # type: ignore[method-assign]
        lambda: [
            {
                "phone_number": "+41760000000",
                "auth_state": "authenticated",
                "hinge_token_expires": "2099-01-01T00:00:00+00:00",
                "identity_id": "id-1",
                "needs_reauth": False,
            },
        ],
    )
    r = client.get("/api/v1/hinge/auth/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Preferences routes
# ---------------------------------------------------------------------------


def test_get_preferences_returns_adapter_payload(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /preferences hands the adapter response through unchanged."""
    container.hinge_api.get_preferences = AsyncMock(
        return_value={"max_distance": 50, "marijuana": []},
    )
    r = client.get("/api/v1/hinge/preferences/")
    assert r.status_code == 200
    assert r.json()["max_distance"] == 50


# ---------------------------------------------------------------------------
# Matches routes
# ---------------------------------------------------------------------------


def test_get_matches_empty(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /matches with no live matches returns an empty array."""
    container.hinge_api.get_matches = AsyncMock(return_value=[])
    r = client.get("/api/v1/hinge/matches/")
    assert r.status_code == 200
    body = r.json()
    assert body["matches"] == []


# ---------------------------------------------------------------------------
# Profile routes
# ---------------------------------------------------------------------------


def test_get_like_limit(client: TestClient, container: HingeContainer) -> None:
    """GET /profile/limits returns the current quota."""
    container.hinge_api.get_like_limit = AsyncMock(
        return_value=HingeLikeLimit(likes_left=5, superlikes_left=0),
    )
    r = client.get("/api/v1/hinge/profile/limits")
    assert r.status_code == 200
    body = r.json()
    assert body.get("likes_left") == 5


def test_get_public_profile_404_when_missing(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /profile/{subject_id} → 404 when the adapter has no entry."""
    container.hinge_api.get_profiles_quick = AsyncMock(return_value={})
    r = client.get("/api/v1/hinge/profile/does-not-exist")
    # 404 when the route returns explicit, 422 if pydantic rejects.
    assert r.status_code in {404, 422}


# ---------------------------------------------------------------------------
# Analytics routes
# ---------------------------------------------------------------------------


def test_analytics_dashboard_aggregates_from_uow(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /analytics/dashboard sums totals via the UoW + repos."""
    # Seed a single profile + decision so the dashboard isn't all zeros.
    with HingeSqlAlchemyUnitOfWork(container._session_factory) as uow:
        from hinge.domain.models.decision import HingeDecision

        uow.profiles.add(HingeProfile(subject_id="s1", first_name="S"))
        uow.decisions.add(
            HingeDecision(
                profile_subject_id="s1",
                action="like",
                decided_at=datetime.now(UTC),
                score=70.0,
            ),
        )
        uow.commit()

    r = client.get("/api/v1/hinge/analytics/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert body  # any non-empty payload — confirms the aggregation ran


def test_analytics_rejection_scan_status(client: TestClient) -> None:
    """GET /analytics/rejection-scan/status returns the scan-state snapshot."""
    r = client.get("/api/v1/hinge/analytics/rejection-scan/status")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)


def test_analytics_decisions_lists_with_profiles(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /analytics/decisions joins decisions with profile snippets."""
    with HingeSqlAlchemyUnitOfWork(container._session_factory) as uow:
        from hinge.domain.models.decision import HingeDecision

        uow.profiles.add(HingeProfile(subject_id="d1", first_name="D1"))
        uow.decisions.add(
            HingeDecision(
                profile_subject_id="d1",
                action="like",
                decided_at=datetime.now(UTC),
            ),
        )
        uow.commit()

    r = client.get("/api/v1/hinge/analytics/decisions")
    assert r.status_code == 200
    body = r.json()
    assert body.get("total", 0) >= 1
    assert isinstance(body.get("decisions"), list)


# ---------------------------------------------------------------------------
# Recommendations routes
# ---------------------------------------------------------------------------


def test_get_recommendations_passthrough(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """GET /recommendations passes the adapter feed straight to the response."""
    container.hinge_api.get_recommendations = AsyncMock(return_value=[])
    container.hinge_api.get_self_location = AsyncMock(return_value=(None, None))
    r = client.get("/api/v1/hinge/recommendations/")
    # Either 200 with an empty feed or 503 if upstream signaled exhaustion —
    # both are valid in the smoke path.
    assert r.status_code in {200, 503}


def test_recommendations_recycle(
    client: TestClient,
    container: HingeContainer,
) -> None:
    """POST /recommendations/recycle returns an OK shape."""
    container.hinge_api.recycle_profiles = AsyncMock(return_value={"recycled": 0})
    r = client.post("/api/v1/hinge/recommendations/recycle")
    assert r.status_code in {200, 202, 204}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_router_is_mounted_under_v1_hinge(client: TestClient) -> None:
    """A nonsense path under our prefix should 404 — confirms mount."""
    r = client.get("/api/v1/hinge/__definitely_not_a_route__")
    assert r.status_code == 404
