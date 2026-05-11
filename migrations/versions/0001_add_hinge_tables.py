"""add hinge tables

Revision ID: 0001
Revises:
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "hinge_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_subject_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("content_id", sa.String(), nullable=True),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.String(), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("is_match", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hinge_profiles",
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender_id", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("location_name", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("hometown", sa.String(), nullable=True),
        sa.Column("job_title", sa.String(), nullable=True),
        sa.Column("works", sa.String(), nullable=True),
        sa.Column("education_attained", sa.Integer(), nullable=True),
        sa.Column("selfie_verified", sa.Boolean(), nullable=True),
        sa.Column("did_just_join", sa.Boolean(), nullable=True),
        sa.Column("last_active_status_id", sa.Integer(), nullable=True),
        sa.Column("children", sa.Integer(), nullable=True),
        sa.Column("dating_intention", sa.Integer(), nullable=True),
        sa.Column("drinking", sa.Integer(), nullable=True),
        sa.Column("drugs", sa.Integer(), nullable=True),
        sa.Column("marijuana", sa.Integer(), nullable=True),
        sa.Column("smoking", sa.Integer(), nullable=True),
        sa.Column("family_plans", sa.Integer(), nullable=True),
        sa.Column("politics", sa.Integer(), nullable=True),
        sa.Column("religions", sa.JSON(), nullable=True),
        sa.Column("ethnicities", sa.JSON(), nullable=True),
        sa.Column("relationship_types", sa.JSON(), nullable=True),
        sa.Column("languages_spoken", sa.JSON(), nullable=True),
        sa.Column("photo_urls", sa.JSON(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("times_seen", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("subject_id"),
    )
    op.create_table(
        "hinge_swipe_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("profiles_seen", sa.Integer(), nullable=True),
        sa.Column("likes_sent", sa.Integer(), nullable=True),
        sa.Column("skips_sent", sa.Integer(), nullable=True),
        sa.Column("notes_sent", sa.Integer(), nullable=True),
        sa.Column("matches", sa.Integer(), nullable=True),
        sa.Column("min_score_threshold", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("hinge_swipe_sessions")
    op.drop_table("hinge_profiles")
    op.drop_table("hinge_decisions")
