"""Hinge Unit of Work — SQLAlchemy implementation."""

from sqlalchemy.orm import Session, sessionmaker

from hinge.domain.ports.unit_of_work import HingeUnitOfWorkPort
from hinge.infrastructure.db.repositories.chat_repo import SqlHingeChatRepo
from hinge.infrastructure.db.repositories.decision_repo import SqlHingeDecisionRepo
from hinge.infrastructure.db.repositories.profile_repo import SqlHingeProfileRepo
from hinge.infrastructure.db.repositories.prompts_repo import SqlHingePromptsRepo
from hinge.infrastructure.db.repositories.session_repo import SqlHingeSessionRepo


class HingeSqlAlchemyUnitOfWork(HingeUnitOfWorkPort):
    """SQLAlchemy implementation of Hinge Unit of Work pattern."""

    profiles: SqlHingeProfileRepo
    decisions: SqlHingeDecisionRepo
    sessions: SqlHingeSessionRepo
    chat: SqlHingeChatRepo
    prompts: SqlHingePromptsRepo

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Store the SQLAlchemy session factory."""
        self._session_factory = session_factory

    def __enter__(self) -> "HingeSqlAlchemyUnitOfWork":
        """Open a new session and initialize repositories."""
        self.session = self._session_factory()
        self.profiles = SqlHingeProfileRepo(self.session)
        self.decisions = SqlHingeDecisionRepo(self.session)
        self.sessions = SqlHingeSessionRepo(self.session)
        self.chat = SqlHingeChatRepo(self.session)
        self.prompts = SqlHingePromptsRepo(self.session)
        return self

    def __exit__(self, *args: object) -> None:
        """Close the session."""
        self.session.close()

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()
