"""Hinge prompt domain model — one row of the dynamic prompt catalog."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HingePrompt:
    """A single Hinge prompt question (e.g. "Two truths and a lie")."""

    prompt_id: str
    text: str
    placeholder: str = ""
    is_selectable: bool = True
    is_new: bool = False
    categories: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    updated_at: datetime | None = None
