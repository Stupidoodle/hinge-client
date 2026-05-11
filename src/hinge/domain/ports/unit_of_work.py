"""Hinge Unit of Work port — abstract boundary for transaction management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from hinge.domain.ports.decision_repo import HingeDecisionRepo
from hinge.domain.ports.profile_repo import HingeProfileRepo
from hinge.domain.ports.session_repo import HingeSessionRepo

if TYPE_CHECKING:
    from hinge.infrastructure.db.repositories.chat_repo import SqlHingeChatRepo


class HingeUnitOfWorkPort(ABC):
    """Abstract Unit of Work with repository access."""

    profiles: HingeProfileRepo
    decisions: HingeDecisionRepo
    sessions: HingeSessionRepo
    chat: SqlHingeChatRepo

    @abstractmethod
    def __enter__(self) -> HingeUnitOfWorkPort:
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
