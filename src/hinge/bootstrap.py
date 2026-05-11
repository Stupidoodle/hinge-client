"""Hinge composition root — wires all DDD layers together.

The single entry point that every long-lived consumer (FastAPI app,
CLI, tests with real adapters) calls to get a fully-wired
``HingeContainer``. Schema management lives in Alembic (``migrations/``);
this module never issues DDL — it only assembles already-defined ports
and adapters.
"""

from dataclasses import dataclass, field

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hinge.application.services.chat_sync_service import ChatSyncService
from hinge.application.services.sendbird_ws import SendbirdWsBridge
from hinge.client import HingeClient
from hinge.core.config import Settings, get_settings
from hinge.domain.ports.hinge_api_port import HingeApiPort
from hinge.domain.ports.scorer_port import HingeScorerPort
from hinge.domain.ports.unit_of_work import HingeUnitOfWorkPort
from hinge.infrastructure.db.mappers import start_hinge_mappers
from hinge.infrastructure.db.unit_of_work import HingeSqlAlchemyUnitOfWork
from hinge.infrastructure.hinge.adapter import HingeApiAdapter
from hinge.infrastructure.scoring.rule_based import HingeRuleBasedScorer
from hinge.prompts_manager import HingePromptsManager


@dataclass
class HingeContainer:
    """Hinge dependency-injection container.

    A plain dataclass (POPO) that holds every wired-up port + service.
    Created by ``bootstrap_hinge`` and consumed by the API/CLI layer.
    """

    hinge_api: HingeApiPort
    scorer: HingeScorerPort
    _client: HingeClient = field(repr=False)
    _session_factory: sessionmaker[Session] = field(repr=False)
    sendbird_ws: SendbirdWsBridge | None = field(default=None, repr=False)
    chat_sync: ChatSyncService | None = field(default=None, repr=False)

    @property
    def uow(self) -> HingeUnitOfWorkPort:
        """Return a new Unit of Work for a database transaction."""
        return HingeSqlAlchemyUnitOfWork(self._session_factory)

    @property
    def prompts_manager(self) -> HingePromptsManager | None:
        """Return the prompts manager (loaded from cache or fetched)."""
        return self._client.prompts_manager

    async def ensure_prompts(self) -> HingePromptsManager | None:
        """Lazy-fetch the prompt catalogue if missing and auth is fresh."""
        if self._client.prompts_manager is not None:
            return self._client.prompts_manager
        if self._client.auth_state != HingeClient.AUTH_AUTHENTICATED:
            return None
        return await self._client.fetch_prompts()


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Build a SQLAlchemy sessionmaker for the given DB URL.

    Mappers are started here so they only register once per process.
    """
    start_hinge_mappers()
    engine = create_engine(database_url, future=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def bootstrap_hinge(
    session_factory: sessionmaker[Session] | None = None,
    *,
    settings: Settings | None = None,
    phone_number: str | None = None,
) -> HingeContainer:
    """Wire the Hinge module and return a fully-configured container.

    If no ``session_factory`` is supplied, one is built from
    ``settings.DATABASE_URL``. The session_factory must be against a
    schema that has already been migrated to ``alembic upgrade head``.

    Args:
        session_factory: Pre-built SQLAlchemy session factory.
        settings: Application settings (defaults to ``get_settings()``).
        phone_number: Hinge account phone. Falls back to
            ``settings.HINGE_PHONE_NUMBER`` then to empty string
            (client starts unauthenticated).

    Returns:
        Wired ``HingeContainer`` ready for use.

    """
    settings = settings or get_settings()
    session_factory = session_factory or build_session_factory(settings.DATABASE_URL)

    effective_phone = phone_number or settings.HINGE_PHONE_NUMBER or ""

    client = HingeClient(phone_number=effective_phone)
    hinge_api = HingeApiAdapter(client)
    scorer = HingeRuleBasedScorer()
    chat_sync = ChatSyncService(api=hinge_api, uow_factory=session_factory)

    return HingeContainer(
        hinge_api=hinge_api,
        scorer=scorer,
        _client=client,
        _session_factory=session_factory,
        chat_sync=chat_sync,
    )
