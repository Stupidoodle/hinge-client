"""SQLAlchemy Hinge decision repository."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from hinge.domain.models.decision import HingeDecision
from hinge.domain.ports.decision_repo import HingeDecisionRepo
from hinge.infrastructure.db.tables.decision import hinge_decision_table
from hinge.infrastructure.db.tables.profile import hinge_profile_table


class SqlHingeDecisionRepo(HingeDecisionRepo):
    """SQLAlchemy-backed Hinge decision repository."""

    def __init__(self, session: Session) -> None:
        """Bind this repository to a SQLAlchemy session."""
        self._session = session

    def add(self, decision: HingeDecision) -> None:
        """Add a new decision."""
        self._session.add(decision)

    def get_by_subject(self, subject_id: str) -> HingeDecision | None:
        """Get the latest decision for a subject."""
        return self._session.execute(
            select(HingeDecision)
            .where(hinge_decision_table.c.profile_subject_id == subject_id)
            .order_by(hinge_decision_table.c.decided_at.desc())
            .limit(1),
        ).scalar_one_or_none()

    def decided_subject_ids(self, subject_ids: list[str]) -> set[str]:
        """Return the subset of subject_ids that have decisions."""
        if not subject_ids:
            return set()
        rows = self._session.execute(
            select(hinge_decision_table.c.profile_subject_id).where(
                hinge_decision_table.c.profile_subject_id.in_(subject_ids),
            ),
        ).scalars()
        return set(rows)

    def count_by_action(self, action: str) -> int:
        """Count decisions by action type."""
        return (
            self._session.execute(
                select(func.count()).where(
                    hinge_decision_table.c.action == action,
                ),
            ).scalar()
            or 0
        )

    def count(self) -> int:
        """Count total decisions."""
        return (
            self._session.execute(
                select(func.count()).select_from(hinge_decision_table),
            ).scalar()
            or 0
        )

    def count_matches(self) -> int:
        """Count outgoing likes that resulted in matches."""
        return (
            self._session.execute(
                select(func.count()).where(
                    hinge_decision_table.c.is_match.is_(True),
                    hinge_decision_table.c.action.in_(
                        ("like", "note", "superlike"),
                    ),
                ),
            ).scalar()
            or 0
        )

    def list_recent(self, *, limit: int = 50) -> list[HingeDecision]:
        """List recent decisions."""
        return list(
            self._session.execute(
                select(HingeDecision)
                .order_by(hinge_decision_table.c.decided_at.desc())
                .limit(limit),
            ).scalars(),
        )

    def list_with_profiles(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List decisions joined with profile data."""
        rows = self._session.execute(
            select(
                hinge_decision_table.c.profile_subject_id,
                hinge_decision_table.c.action,
                hinge_decision_table.c.score,
                hinge_decision_table.c.reasoning,
                hinge_decision_table.c.is_match,
                hinge_decision_table.c.decided_at,
                hinge_profile_table.c.first_name,
                hinge_profile_table.c.age,
                hinge_profile_table.c.photo_urls,
            )
            .outerjoin(
                hinge_profile_table,
                hinge_decision_table.c.profile_subject_id
                == hinge_profile_table.c.subject_id,
            )
            .order_by(hinge_decision_table.c.decided_at.desc())
            .limit(limit)
            .offset(offset),
        ).all()

        return [
            {
                "subject_id": row.profile_subject_id,
                "name": row.first_name,
                "age": row.age,
                "photo_url": row.photo_urls[0] if row.photo_urls else None,
                "score": row.score,
                "action": row.action,
                "reasoning": row.reasoning,
                "matched": row.is_match,
                "decided_at": str(row.decided_at) if row.decided_at else None,
            }
            for row in rows
        ]

    def avg_score(self) -> float:
        """Average score across all decisions."""
        result = self._session.execute(
            select(func.avg(hinge_decision_table.c.score)),
        ).scalar()
        return float(result) if result else 0.0

    def daily_stats(self, since_days: int = 30) -> list[dict]:
        """Get daily aggregated stats."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

        rows = self._session.execute(
            select(
                func.date(hinge_decision_table.c.decided_at).label("date"),
                func.count().label("total"),
                func.sum(
                    func.cast(
                        hinge_decision_table.c.action.in_(
                            ("like", "note", "superlike"),
                        ),
                        type_=Integer,
                    ),
                ).label("liked"),
                func.sum(
                    func.cast(
                        hinge_decision_table.c.action == "skip",
                        type_=Integer,
                    ),
                ).label("skipped"),
                func.sum(
                    func.cast(
                        hinge_decision_table.c.is_match.is_(True),
                        type_=Integer,
                    ),
                ).label("matches"),
                func.avg(hinge_decision_table.c.score).label("avg_score"),
            )
            .where(hinge_decision_table.c.decided_at >= cutoff)
            .group_by(func.date(hinge_decision_table.c.decided_at))
            .order_by(func.date(hinge_decision_table.c.decided_at)),
        ).all()

        return [
            {
                "date": str(row.date),
                "total": row.total or 0,
                "liked": row.liked or 0,
                "skipped": row.skipped or 0,
                "matches": row.matches or 0,
                "avg_score": round(float(row.avg_score or 0), 1),
            }
            for row in rows
        ]
