"""Hinge decision repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from hinge.domain.models.decision import HingeDecision


class HingeDecisionRepo(ABC):
    """Abstract repository for Hinge decision persistence."""

    @abstractmethod
    def add(self, decision: HingeDecision) -> None:
        """Add a new decision."""
        raise NotImplementedError

    @abstractmethod
    def get_by_subject(self, subject_id: str) -> HingeDecision | None:
        """Get the latest decision for a subject."""
        raise NotImplementedError

    @abstractmethod
    def decided_subject_ids(self, subject_ids: list[str]) -> set[str]:
        """Return the subset of subject_ids that have decisions."""
        raise NotImplementedError

    @abstractmethod
    def count_by_action(self, action: str) -> int:
        """Count decisions by action type."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Count total decisions."""
        raise NotImplementedError

    @abstractmethod
    def count_matches(self) -> int:
        """Count decisions that resulted in matches."""
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, *, limit: int = 50) -> list[HingeDecision]:
        """List recent decisions."""
        raise NotImplementedError

    @abstractmethod
    def list_with_profiles(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List decisions joined with profile data."""
        raise NotImplementedError

    @abstractmethod
    def avg_score(self) -> float:
        """Average score across all decisions."""
        raise NotImplementedError

    @abstractmethod
    def daily_stats(self, since_days: int = 30) -> list[dict]:
        """Get daily aggregated stats."""
        raise NotImplementedError
