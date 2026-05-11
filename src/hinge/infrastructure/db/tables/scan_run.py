"""Hinge rejection scan run table definition."""

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Table,
    func,
)

from hinge.infrastructure.db.metadata import metadata

hinge_scan_run_table = Table(
    "hinge_scan_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("started_at", DateTime, nullable=False, server_default=func.now()),
    Column("finished_at", DateTime),
    Column("total_fetched", Integer, default=0),
    Column("unique_pool", Integer, default=0),
    Column("batches", Integer, default=0),
    Column("disappeared", Integer, default=0),
    Column("marked_rejected", Integer, default=0),
    Column("trigger", String, default="manual"),  # "manual" or "scheduled"
    Column("rate_limit_retries", Integer, default=0),
    Column("error", String),
)
