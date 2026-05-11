"""Hinge profile scorer port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from hinge.domain.models.profile import HingeProfile


class HingeScorerPort(ABC):
    """Abstract interface for Hinge profile scoring."""

    @abstractmethod
    async def score(self, profile: HingeProfile) -> tuple[float, str]:
        """Score a profile.

        Args:
            profile: The profile to evaluate.

        Returns:
            Tuple of (score 0-100, reasoning string).

        """
        raise NotImplementedError
