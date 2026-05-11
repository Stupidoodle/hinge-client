"""Hinge swipe session repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from hinge.domain.models.swipe_session import HingeSwipeSession


class HingeSessionRepo(ABC):
    """Abstract repository for Hinge swipe session persistence."""

    @abstractmethod
    def add(self, session: HingeSwipeSession) -> None:
        """Add a new session."""
        raise NotImplementedError

    @abstractmethod
    def get(self, session_id: int) -> HingeSwipeSession | None:
        """Get a session by ID."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Count total sessions."""
        raise NotImplementedError

    @abstractmethod
    def update(self, session: HingeSwipeSession) -> None:
        """Update an existing session."""
        raise NotImplementedError
