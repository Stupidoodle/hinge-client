"""Hinge decision table definition."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Table,
    func,
)

from hinge.infrastructure.db.metadata import metadata

hinge_decision_table = Table(
    "hinge_decisions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("profile_subject_id", String, nullable=False),
    Column("action", String, nullable=False),
    Column("content_id", String),
    Column("comment", String),
    Column("score", Float),
    Column("reasoning", String),
    Column("decided_at", DateTime, nullable=False, server_default=func.now()),
    Column("session_id", Integer),
    Column("is_match", Boolean, default=False),
)
