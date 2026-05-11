"""SQLAlchemy implementation of the Hinge prompts catalog repository."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from hinge.domain.models.prompt import HingePrompt
from hinge.domain.ports.prompts_repo import HingePromptsRepo
from hinge.infrastructure.db.tables.prompt import hinge_prompt_table


def _to_row(p: HingePrompt) -> dict[str, object]:
    """Project a HingePrompt onto a row dict for upsert."""
    return {
        "prompt_id": p.prompt_id,
        "text": p.text,
        "placeholder": p.placeholder,
        "is_selectable": p.is_selectable,
        "is_new": p.is_new,
        "categories": p.categories,
        "content_types": p.content_types,
        "updated_at": p.updated_at or datetime.now(UTC),
    }


class SqlHingePromptsRepo(HingePromptsRepo):
    """SQLAlchemy-backed prompts catalog repository."""

    def __init__(self, session: Session) -> None:
        """Bind this repository to a SQLAlchemy session."""
        self._session = session

    def get(self, prompt_id: str) -> HingePrompt | None:
        """Fetch one prompt by ID."""
        return self._session.get(HingePrompt, prompt_id)

    def get_text(self, prompt_id: str) -> str | None:
        """Return the display text for one prompt — hot path used by mappers."""
        text = self._session.execute(
            select(hinge_prompt_table.c.text).where(
                hinge_prompt_table.c.prompt_id == prompt_id,
            ),
        ).scalar_one_or_none()
        return text

    def list_all(self) -> list[HingePrompt]:
        """Return every prompt, ordered by ID."""
        stmt = select(HingePrompt).order_by(hinge_prompt_table.c.prompt_id)
        return list(self._session.execute(stmt).scalars())

    def count(self) -> int:
        """Total number of cached prompts."""
        return int(
            self._session.execute(
                select(func.count()).select_from(hinge_prompt_table),
            ).scalar_one(),
        )

    def bulk_upsert(self, prompts: list[HingePrompt]) -> int:
        """Insert or update a batch of prompts in one statement."""
        if not prompts:
            return 0
        rows = [_to_row(p) for p in prompts]
        stmt = sqlite_insert(hinge_prompt_table).values(rows)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in hinge_prompt_table.columns
            if col.name != "prompt_id"
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["prompt_id"],
            set_=update_cols,
        )
        self._session.execute(stmt)
        return len(rows)
