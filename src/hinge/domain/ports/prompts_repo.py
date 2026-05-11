"""Hinge prompts catalog repository port."""

from abc import ABC, abstractmethod

from hinge.domain.models.prompt import HingePrompt


class HingePromptsRepo(ABC):
    """Abstract repository for the Hinge prompt catalog.

    The catalog is small (a few hundred rows), static-ish, and queried
    by ``prompt_id`` on every profile render. Implementations should
    treat ``get_text`` as the hot path.
    """

    @abstractmethod
    def get(self, prompt_id: str) -> HingePrompt | None:
        """Fetch a single prompt by its Hinge ID."""
        raise NotImplementedError

    @abstractmethod
    def get_text(self, prompt_id: str) -> str | None:
        """Return just the display text for a prompt, or None if unknown."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[HingePrompt]:
        """Return every prompt in the catalog."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return how many prompts are stored. 0 means catalog is unloaded."""
        raise NotImplementedError

    @abstractmethod
    def bulk_upsert(self, prompts: list[HingePrompt]) -> int:
        """Insert or update a batch of prompts. Returns the number written."""
        raise NotImplementedError
