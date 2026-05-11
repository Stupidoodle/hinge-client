"""Custom SQLAlchemy column types."""

import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class JsonList(TypeDecorator):
    """SQLAlchemy type for serializing list[str] as JSON Text."""

    impl = Text
    cache_ok = True

    def process_bind_param(
        self,
        value: list[Any] | None,
        dialect: Dialect,
    ) -> str:
        """Serialize list to JSON string."""
        return json.dumps(value) if value else "[]"

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,
    ) -> list[Any]:
        """Deserialize JSON string to list."""
        return json.loads(value) if value else []
