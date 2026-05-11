"""add hinge prompts catalog table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-11 00:00:02.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the hinge_prompts catalog table.

    Replaces the flat-file prompts_cache.json mirror with proper DB
    storage. Hinge's prompt catalog is small (~few hundred rows) and
    queried per-profile-render, so a primary-key lookup is the hot path.
    """
    op.create_table(
        "hinge_prompts",
        sa.Column("prompt_id", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("placeholder", sa.String(), server_default="", nullable=False),
        sa.Column(
            "is_selectable",
            sa.Boolean(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("is_new", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("categories", sa.Text(), server_default="[]", nullable=False),
        sa.Column("content_types", sa.Text(), server_default="[]", nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("prompt_id"),
    )


def downgrade() -> None:
    """Drop the hinge_prompts catalog table."""
    op.drop_table("hinge_prompts")
