"""Hinge profile repository port."""

from abc import ABC, abstractmethod

from hinge.domain.models.profile import HingeProfile


class HingeProfileRepo(ABC):
    """Abstract repository for Hinge profile persistence."""

    @abstractmethod
    def add(self, profile: HingeProfile) -> None:
        """Add or update a profile."""
        raise NotImplementedError

    @abstractmethod
    def get(self, subject_id: str) -> HingeProfile | None:
        """Get a profile by subject_id."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self, *, limit: int = 50, offset: int = 0) -> list[HingeProfile]:
        """List profiles with pagination.

        Named ``list_all`` (not ``list``) to avoid shadowing the ``list``
        builtin inside the class scope, which breaks other annotations
        on the same class that use ``list[HingeProfile]``.
        """
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Count total profiles."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        *,
        name: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[HingeProfile]:
        """Search profiles by criteria."""
        raise NotImplementedError

    @abstractmethod
    def get_undecided(self) -> list[HingeProfile]:
        """Get all profiles with no decision recorded."""
        raise NotImplementedError

    @abstractmethod
    def get_undecided_subject_ids(self) -> set[str]:
        """Get subject_ids of all undecided, non-rejected profiles."""
        raise NotImplementedError

    @abstractmethod
    def mark_likely_rejected(self, subject_ids: set[str]) -> int:
        """Flag profiles as likely rejected. Returns count updated."""
        raise NotImplementedError

    @abstractmethod
    def count_by_rejection_type(self, rejection_type: str) -> int:
        """Count profiles flagged with a specific rejection_type ('passed' / 'gone')."""
        raise NotImplementedError

    @abstractmethod
    def get_likely_rejected(self) -> list[HingeProfile]:
        """Get all profiles flagged as likely rejected."""
        raise NotImplementedError

    @abstractmethod
    def increment_miss_count(self, subject_ids: set[str]) -> int:
        """Increment miss_count for profiles absent from a scan."""
        raise NotImplementedError

    @abstractmethod
    def reset_miss_count(self, subject_ids: set[str]) -> int:
        """Reset miss_count to 0 for profiles present in a scan."""
        raise NotImplementedError

    @abstractmethod
    def clear_false_rejections(self, present_ids: set[str]) -> int:
        """Un-reject profiles that reappeared in the feed."""
        raise NotImplementedError

    @abstractmethod
    def set_rejection_type(self, subject_id: str, rejection_type: str) -> None:
        """Set rejection_type ('passed' or 'gone') on a rejected profile."""
        raise NotImplementedError

    @abstractmethod
    def get_untyped_rejections(self) -> set[str]:
        """Get subject_ids of rejected profiles with no rejection_type."""
        raise NotImplementedError
