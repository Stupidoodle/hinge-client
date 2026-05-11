"""Hinge prompt catalog table definition."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
    Table,
)

from hinge.infrastructure.db.metadata import metadata
from hinge.infrastructure.db.types import JsonList

hinge_prompt_table = Table(
    "hinge_prompts",
    metadata,
    Column("prompt_id", String, primary_key=True),
    Column("text", String, nullable=False),
    Column("placeholder", String, nullable=False, server_default=""),
    Column("is_selectable", Boolean, nullable=False, server_default="1"),
    Column("is_new", Boolean, nullable=False, server_default="0"),
    Column("categories", JsonList, nullable=False, server_default="[]"),
    Column("content_types", JsonList, nullable=False, server_default="[]"),
    Column("updated_at", DateTime),
)
