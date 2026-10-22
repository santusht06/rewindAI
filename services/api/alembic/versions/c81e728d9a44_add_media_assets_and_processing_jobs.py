"""add media assets and processing jobs tables and movie readiness fields

Revision ID: c81e728d9a44
Revises: a41c8f9d2e70
Create Date: 2026-10-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c81e728d9a44"
down_revision: str | Sequence[str] | None = "a41c8f9d2e70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add playback readiness and stream URL columns to movies table
    op.add_column("movies", sa.Column("stream_url", sa.String(length=500), nullable=True))
    op.add_column("movies", sa.Column("poster_url", sa.String(length=500), nullable=True))
    op.add_column(
        "movies",
        sa.Column("is_playback_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "movies",
        sa.Column("is_ai_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 2. Create media_assets table
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("movie_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("stream_url", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("codec", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_movie_id", "media_assets", ["movie_id"])
    op.create_index("ix_media_assets_asset_type", "media_assets", ["asset_type"])
    op.create_index("ix_media_assets_status", "media_assets", ["status"])

    # 3. Create processing_jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("movie_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False, server_default="uploaded"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_retryable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_playback_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_ai_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_jobs_movie_id", "processing_jobs", ["movie_id"])
    op.create_index("ix_processing_jobs_stage", "processing_jobs", ["stage"])


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_stage", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_movie_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")

    op.drop_index("ix_media_assets_status", table_name="media_assets")
    op.drop_index("ix_media_assets_asset_type", table_name="media_assets")
    op.drop_index("ix_media_assets_movie_id", table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_column("movies", "is_ai_ready")
    op.drop_column("movies", "is_playback_ready")
    op.drop_column("movies", "poster_url")
    op.drop_column("movies", "stream_url")
