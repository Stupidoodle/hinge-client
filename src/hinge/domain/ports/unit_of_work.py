"""Hinge Unit of Work port — abstract boundary for transaction management."""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from hinge.domain.ports.chat_repo import HingeChatRepo
from hinge.domain.ports.decision_repo import HingeDecisionRepo
from hinge.domain.ports.profile_repo import HingeProfileRepo
from hinge.domain.ports.session_repo import HingeSessionRepo


class HingeUnitOfWorkPort(ABC):
    """Abstract Unit of Work that aggregates the four Hinge repositories.

    Concrete implementations open a SQLAlchemy session in ``__enter__`` and
    expose it via ``session`` so routes that need raw SQL (analytics
    aggregates, hand-rolled queries) can still go through the UoW boundary
    without breaking the port abstraction.
    """

    session: Session
    profiles: HingeProfileRepo
    decisions: HingeDecisionRepo
    sessions: HingeSessionRepo
    chat: HingeChatRepo

    @abstractmethod
    def __enter__(self) -> "HingeUnitOfWorkPort":
        """Open a new session and initialize repositories."""
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, *args: object) -> None:
        """Close the session."""
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction."""
        raise NotImplementedError
