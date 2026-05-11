"""Hinge swipe session table definition."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Table,
    func,
)

from hinge.infrastructure.db.metadata import metadata

hinge_session_table = Table(
    "hinge_swipe_sessions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("started_at", DateTime, nullable=False, server_default=func.now()),
    Column("ended_at", DateTime),
    Column("profiles_seen", Integer, default=0),
    Column("likes_sent", Integer, default=0),
    Column("skips_sent", Integer, default=0),
    Column("notes_sent", Integer, default=0),
    Column("matches", Integer, default=0),
    Column("min_score_threshold", Float, default=0.0),
)
