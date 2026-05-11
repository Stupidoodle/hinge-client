"""SQLAlchemy session factory for hinge."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hinge.infrastructure.db.metadata import metadata


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory.

    Args:
        database_url: SQLAlchemy database URL (e.g. sqlite:///hinge.db).

    Returns:
        Configured sessionmaker instance bound to a fresh engine.
        Calls ``metadata.create_all`` so dev databases are usable
        without running migrations first.

    """
    engine = create_engine(database_url, echo=False)
    metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
