"""add character metadata to curated story facts

Revision ID: a41c8f9d2e70
Revises: de72b6e86a31
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a41c8f9d2e70"
down_revision: str | Sequence[str] | None = "de72b6e86a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subtitle_cues",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_version_id", sa.String(length=36), nullable=False),
        sa.Column("movie_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("start_time_seconds", sa.Float(), nullable=False),
        sa.Column("end_time_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker", sa.String(length=100), nullable=True),
        sa.CheckConstraint("start_time_seconds >= 0", name="chk_cue_start_non_negative"),
        sa.CheckConstraint("end_time_seconds >= start_time_seconds", name="chk_cue_end_after_start"),
        sa.ForeignKeyConstraint(["content_version_id"], ["content_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_version_id", "ordinal", name="uq_version_cue_ordinal"),
    )
    op.create_index("ix_subtitle_cues_content_version_id", "subtitle_cues", ["content_version_id"])
    op.create_index("ix_subtitle_cues_movie_id", "subtitle_cues", ["movie_id"])
    op.create_index("ix_subtitle_cues_start_time_seconds", "subtitle_cues", ["start_time_seconds"])
    op.create_index("ix_subtitle_cues_end_time_seconds", "subtitle_cues", ["end_time_seconds"])
    op.add_column("story_facts", sa.Column("character_name", sa.String(length=120), nullable=True))
    op.add_column("story_facts", sa.Column("relationship", sa.String(length=240), nullable=True))
    op.create_index(
        "ix_story_facts_character_name",
        "story_facts",
        ["character_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_story_facts_character_name", table_name="story_facts")
    op.drop_column("story_facts", "relationship")
    op.drop_column("story_facts", "character_name")
    op.drop_index("ix_subtitle_cues_end_time_seconds", table_name="subtitle_cues")
    op.drop_index("ix_subtitle_cues_start_time_seconds", table_name="subtitle_cues")
    op.drop_index("ix_subtitle_cues_movie_id", table_name="subtitle_cues")
    op.drop_index("ix_subtitle_cues_content_version_id", table_name="subtitle_cues")
    op.drop_table("subtitle_cues")
