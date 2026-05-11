"""SQLAlchemy Hinge profile repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from hinge.domain.models.profile import HingeProfile
from hinge.domain.ports.profile_repo import HingeProfileRepo
from hinge.infrastructure.db.tables.decision import hinge_decision_table
from hinge.infrastructure.db.tables.profile import hinge_profile_table


class SqlHingeProfileRepo(HingeProfileRepo):
    """SQLAlchemy-backed Hinge profile repository."""

    def __init__(self, session: Session) -> None:
        """Bind this repository to a SQLAlchemy session."""
        self._session = session

    def add(self, profile: HingeProfile) -> None:
        """Add a new profile (or merge if exists)."""
        self._session.merge(profile)

    def get(self, subject_id: str) -> HingeProfile | None:
        """Get a profile by subject_id."""
        return self._session.get(HingeProfile, subject_id)

    def list_all(self, *, limit: int = 50, offset: int = 0) -> list[HingeProfile]:
        """List profiles with pagination."""
        return list(
            self._session.execute(
                select(HingeProfile)
                .order_by(hinge_profile_table.c.last_seen_at.desc())
                .limit(limit)
                .offset(offset),
            ).scalars(),
        )

    def count(self) -> int:
        """Count total profiles."""
        return (
            self._session.execute(
                select(func.count()).select_from(hinge_profile_table),
            ).scalar()
            or 0
        )

    def search(
        self,
        *,
        name: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[HingeProfile]:
        """Search profiles by criteria."""
        stmt = select(HingeProfile)
        if name:
            stmt = stmt.where(hinge_profile_table.c.first_name.ilike(f"%{name}%"))
        if min_age is not None:
            stmt = stmt.where(hinge_profile_table.c.age >= min_age)
        if max_age is not None:
            stmt = stmt.where(hinge_profile_table.c.age <= max_age)
        return list(self._session.execute(stmt).scalars())

    def get_undecided(self) -> list[HingeProfile]:
        """Get all profiles with no decision recorded and not rejected."""
        decided_subq = (
            select(hinge_decision_table.c.profile_subject_id)
            .distinct()
            .scalar_subquery()
        )
        stmt = (
            select(HingeProfile)
            .where(
                hinge_profile_table.c.subject_id.notin_(decided_subq),
                hinge_profile_table.c.likely_rejected.is_(False),
            )
            .order_by(hinge_profile_table.c.last_seen_at.desc())
        )
        return list(self._session.execute(stmt).scalars())

    def get_undecided_subject_ids(self) -> set[str]:
        """Get subject_ids of all undecided, non-rejected profiles."""
        decided_subq = (
            select(hinge_decision_table.c.profile_subject_id)
            .distinct()
            .scalar_subquery()
        )
        stmt = select(hinge_profile_table.c.subject_id).where(
            hinge_profile_table.c.subject_id.notin_(decided_subq),
            hinge_profile_table.c.likely_rejected.is_(False),
        )
        return set(self._session.execute(stmt).scalars())

    def mark_likely_rejected(self, subject_ids: set[str]) -> int:
        """Flag profiles as likely rejected. Returns count updated."""
        if not subject_ids:
            return 0
        now = datetime.now(timezone.utc)
        stmt = (
            update(hinge_profile_table)
            .where(hinge_profile_table.c.subject_id.in_(subject_ids))
            .values(likely_rejected=True, rejection_detected_at=now)
        )
        result = self._session.execute(stmt)
        return result.rowcount

    def count_by_rejection_type(self, rejection_type: str) -> int:
        """Count rejected profiles by type ('passed' or 'gone')."""
        return (
            self._session.execute(
                select(func.count())
                .select_from(hinge_profile_table)
                .where(
                    hinge_profile_table.c.likely_rejected.is_(True),
                    hinge_profile_table.c.rejection_type == rejection_type,
                ),
            ).scalar()
            or 0
        )

    def get_likely_rejected(self) -> list[HingeProfile]:
        """Get all profiles flagged as likely rejected."""
        stmt = (
            select(HingeProfile)
            .where(hinge_profile_table.c.likely_rejected.is_(True))
            .order_by(hinge_profile_table.c.rejection_detected_at.desc())
        )
        return list(self._session.execute(stmt).scalars())

    def increment_miss_count(self, subject_ids: set[str]) -> int:
        """Increment miss_count for profiles absent from a scan."""
        if not subject_ids:
            return 0
        stmt = (
            update(hinge_profile_table)
            .where(hinge_profile_table.c.subject_id.in_(subject_ids))
            .values(miss_count=hinge_profile_table.c.miss_count + 1)
        )
        return self._session.execute(stmt).rowcount

    def reset_miss_count(self, subject_ids: set[str]) -> int:
        """Reset miss_count to 0 for profiles present in a scan."""
        if not subject_ids:
            return 0
        stmt = (
            update(hinge_profile_table)
            .where(
                hinge_profile_table.c.subject_id.in_(subject_ids),
                hinge_profile_table.c.miss_count > 0,
            )
            .values(miss_count=0)
        )
        return self._session.execute(stmt).rowcount

    def clear_false_rejections(self, present_ids: set[str]) -> int:
        """Un-reject profiles that reappeared in the feed."""
        if not present_ids:
            return 0
        stmt = (
            update(hinge_profile_table)
            .where(
                hinge_profile_table.c.subject_id.in_(present_ids),
                hinge_profile_table.c.likely_rejected.is_(True),
            )
            .values(
                likely_rejected=False,
                rejection_detected_at=None,
                rejection_type=None,
                miss_count=0,
            )
        )
        return self._session.execute(stmt).rowcount

    def set_rejection_type(self, subject_id: str, rejection_type: str) -> None:
        """Set rejection_type ('passed' or 'gone') on a rejected profile."""
        stmt = (
            update(hinge_profile_table)
            .where(hinge_profile_table.c.subject_id == subject_id)
            .values(rejection_type=rejection_type)
        )
        self._session.execute(stmt)

    def get_untyped_rejections(self) -> set[str]:
        """Get subject_ids of rejected profiles with no rejection_type."""
        stmt = select(hinge_profile_table.c.subject_id).where(
            hinge_profile_table.c.likely_rejected.is_(True),
            hinge_profile_table.c.rejection_type.is_(None),
        )
        return set(self._session.execute(stmt).scalars())
