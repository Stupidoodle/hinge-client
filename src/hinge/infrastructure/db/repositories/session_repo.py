"""SQLAlchemy Hinge swipe session repository."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hinge.domain.models.swipe_session import HingeSwipeSession
from hinge.domain.ports.session_repo import HingeSessionRepo
from hinge.infrastructure.db.tables.session import hinge_session_table


class SqlHingeSessionRepo(HingeSessionRepo):
    """SQLAlchemy-backed Hinge swipe session repository."""

    def __init__(self, session: Session) -> None:
        """Bind this repository to a SQLAlchemy session."""
        self._session = session

    def add(self, session: HingeSwipeSession) -> None:
        """Add a new session."""
        self._session.add(session)

    def get(self, session_id: int) -> HingeSwipeSession | None:
        """Get a session by ID."""
        return self._session.get(HingeSwipeSession, session_id)

    def count(self) -> int:
        """Count total sessions."""
        return (
            self._session.execute(
                select(func.count()).select_from(hinge_session_table),
            ).scalar()
            or 0
        )

    def update(self, session: HingeSwipeSession) -> None:
        """Update an existing session."""
        self._session.merge(session)
