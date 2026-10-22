"""SQLAlchemy ORM table definitions mapping domain entities and constraints.

Implements 03_DOMAIN_MODEL_AND_DATABASE, 09_database_erd.mmd, and NFR-SEC-002.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.infrastructure.database import Base

__all__ = ["Base"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class MovieTable(Base):
    """Canonical title / movie record."""

    __tablename__ = "movies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=7200)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    stream_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_playback_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ai_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    @property
    def display_title(self) -> str:
        return self.title

    @property
    def year(self) -> int | None:
        return self.release_year


    # Relationships
    content_versions: Mapped[list[ContentVersionTable]] = relationship(
        "ContentVersionTable", back_populates="movie", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[ViewingSessionTable]] = relationship(
        "ViewingSessionTable", back_populates="movie", cascade="all, delete-orphan"
    )
    media_assets: Mapped[list[MediaAssetTable]] = relationship(
        "MediaAssetTable", back_populates="movie", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list[ProcessingJobTable]] = relationship(
        "ProcessingJobTable", back_populates="movie", cascade="all, delete-orphan"
    )


class MediaAssetTable(Base):
    """Media asset binary reference (video, HLS stream, audio, subtitles)."""

    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    stream_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    movie: Mapped[MovieTable] = relationship("MovieTable", back_populates="media_assets")


class ProcessingJobTable(Base):
    """Asynchronous media processing job tracking."""

    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="uploaded", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    is_retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_playback_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ai_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    movie: Mapped[MovieTable] = relationship("MovieTable", back_populates="processing_jobs")



class ContentVersionTable(Base):
    """Versioned content asset and index state for a movie."""

    __tablename__ = "content_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="srt")
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Unique constraint per movie and version
    __table_args__ = (
        UniqueConstraint("movie_id", "version_number", name="uq_movie_version_number"),
    )

    # Relationships
    movie: Mapped[MovieTable] = relationship("MovieTable", back_populates="content_versions")
    chunks: Mapped[list[SubtitleChunkTable]] = relationship(
        "SubtitleChunkTable", back_populates="content_version", cascade="all, delete-orphan"
    )
    facts: Mapped[list[StoryFactTable]] = relationship(
        "StoryFactTable", back_populates="content_version", cascade="all, delete-orphan"
    )
    subtitle_cues: Mapped[list[SubtitleCueTable]] = relationship(
        "SubtitleCueTable", back_populates="content_version", cascade="all, delete-orphan"
    )


class SubtitleChunkTable(Base):
    """Timestamped dialogue chunk with embedding."""

    __tablename__ = "subtitle_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    end_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    start_time_formatted: Mapped[str] = mapped_column(String(20), nullable=False)
    end_time_formatted: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("content_version_id", "ordinal", name="uq_version_chunk_ordinal"),
        CheckConstraint("start_time_seconds >= 0", name="chk_start_non_negative"),
        CheckConstraint("end_time_seconds >= start_time_seconds", name="chk_end_after_start"),
    )

    # Relationships
    content_version: Mapped[ContentVersionTable] = relationship(
        "ContentVersionTable", back_populates="chunks"
    )


class SubtitleCueTable(Base):
    """An individual authorized subtitle cue retained for line-level selection."""

    __tablename__ = "subtitle_cues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    end_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("content_version_id", "ordinal", name="uq_version_cue_ordinal"),
        CheckConstraint("start_time_seconds >= 0", name="chk_cue_start_non_negative"),
        CheckConstraint("end_time_seconds >= start_time_seconds", name="chk_cue_end_after_start"),
    )

    content_version: Mapped[ContentVersionTable] = relationship(
        "ContentVersionTable", back_populates="subtitle_cues"
    )


class StoryFactTable(Base):
    """Canon plot fact with first reveal boundary timestamp."""

    __tablename__ = "story_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    character_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    relationship_description: Mapped[str | None] = mapped_column("relationship", String(240), nullable=True)
    first_known_at_seconds: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="verified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    content_version: Mapped[ContentVersionTable] = relationship(
        "ContentVersionTable", back_populates="facts"
    )


class ViewingSessionTable(Base):
    """User viewing session with playback progress and spoiler state."""

    __tablename__ = "viewing_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="anonymous", index=True)
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_position_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    progress_source: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    spoiler_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="safe")
    full_spoilers_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    spoiler_confirmation_nonce: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    spoiler_nonce_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint("current_position_seconds >= 0", name="chk_session_position_non_negative"),
    )

    # Relationships
    movie: Mapped[MovieTable] = relationship("MovieTable", back_populates="sessions")
    questions: Mapped[list[QuestionTable]] = relationship(
        "QuestionTable", back_populates="session", cascade="all, delete-orphan"
    )


class QuestionTable(Base):
    """Question submitted during a session with grounded response."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("viewing_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    playback_position_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    spoiler_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="answered")
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    session: Mapped[ViewingSessionTable] = relationship("ViewingSessionTable", back_populates="questions")
    sources: Mapped[list[AnswerSourceTable]] = relationship(
        "AnswerSourceTable", back_populates="question", cascade="all, delete-orphan"
    )


class AnswerSourceTable(Base):
    """Citations linking a question answer to chunks or facts."""

    __tablename__ = "answer_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("subtitle_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    story_fact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("story_facts.id", ondelete="SET NULL"), nullable=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    question: Mapped[QuestionTable] = relationship("QuestionTable", back_populates="sources")


class AuditEventTable(Base):
    """Audit log for security and administrative actions."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
