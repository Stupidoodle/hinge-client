"""Hinge API port — abstract interface for the Hinge API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hinge.domain.models.like_limit import HingeLikeLimit
from hinge.domain.models.match import HingeMatch
from hinge.domain.models.profile import HingeProfile
from hinge.domain.models.recommendation import Recommendation


class HingeApiPort(ABC):
    """Abstract interface for the Hinge API."""

    # Recommendations
    @abstractmethod
    async def get_recommendations(self) -> list[Recommendation]:
        """Fetch recommendation feed."""
        raise NotImplementedError

    @abstractmethod
    async def get_standouts(self) -> list[Recommendation]:
        """Fetch standouts feed."""
        raise NotImplementedError

    @abstractmethod
    async def get_profile_content(
        self,
        subject_ids: list[str],
    ) -> dict[str, HingeProfile]:
        """Fetch full content and build domain profiles."""
        raise NotImplementedError

    @abstractmethod
    async def get_profiles_quick(
        self,
        subject_ids: list[str],
    ) -> dict[str, HingeProfile]:
        """Fetch profile + basic content in one call (v2, no pHash/waveform/poll)."""
        raise NotImplementedError

    @abstractmethod
    async def refresh_demographics(
        self,
        profiles: list[HingeProfile],
    ) -> None:
        """Re-fetch demographics from API and update profiles in-place."""
        raise NotImplementedError

    @abstractmethod
    async def hydrate_profiles(
        self,
        profiles: list[HingeProfile],
    ) -> None:
        """Fetch content and merge into existing profiles in-place."""
        raise NotImplementedError

    # Rating
    @abstractmethod
    async def skip(
        self,
        subject_id: str,
        rating_token: str,
        origin: str,
    ) -> None:
        """Skip a recommendation."""
        raise NotImplementedError

    @abstractmethod
    async def like_photo(
        self,
        subject_id: str,
        rating_token: str,
        origin: str,
        content_id: str,
        url: str,
        cdn_id: str,
        *,
        comment: str | None = None,
        superlike: bool = False,
    ) -> HingeLikeLimit:
        """Like a photo, optionally with a comment."""
        raise NotImplementedError

    @abstractmethod
    async def like_prompt(
        self,
        subject_id: str,
        rating_token: str,
        origin: str,
        content_id: str,
        question: str,
        answer: str,
        *,
        comment: str | None = None,
        superlike: bool = False,
    ) -> HingeLikeLimit:
        """Like a prompt answer, optionally with a comment."""
        raise NotImplementedError

    # Likes & Matches
    @abstractmethod
    async def get_likes_received(self) -> list[HingeProfile]:
        """Fetch profiles who liked you."""
        raise NotImplementedError

    @abstractmethod
    async def get_matches(self) -> list[HingeMatch]:
        """Fetch match list."""
        raise NotImplementedError

    # Profile
    @abstractmethod
    async def get_self_profile(self) -> HingeProfile:
        """Fetch own profile."""
        raise NotImplementedError

    @abstractmethod
    async def update_self_profile(self, updates: dict[str, Any]) -> None:
        """Update own profile."""
        raise NotImplementedError

    @abstractmethod
    async def get_public_profiles(
        self,
        subject_ids: list[str],
    ) -> list[HingeProfile]:
        """Fetch public profiles by IDs."""
        raise NotImplementedError

    # Preferences
    @abstractmethod
    async def get_preferences(self) -> dict[str, Any]:
        """Fetch current preferences."""
        raise NotImplementedError

    @abstractmethod
    async def update_preferences(self, preferences: dict[str, Any]) -> None:
        """Update preferences."""
        raise NotImplementedError

    # Limits
    @abstractmethod
    async def get_like_limit(self) -> HingeLikeLimit:
        """Fetch current like limits."""
        raise NotImplementedError

    # Utility
    @abstractmethod
    async def repeat_profiles(self) -> None:
        """Recycle seen profiles."""
        raise NotImplementedError
