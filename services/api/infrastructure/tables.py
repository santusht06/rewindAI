"""SQLAlchemy ORM table definitions mapping domain entities and constraints.

Implements 03_DOMAIN_MODEL_AND_DATABASE, 09_database_erd.mmd, and NFR-SEC-002.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from services.api.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MovieTable(Base):
    """Canonical title / movie record."""

    __tablename__ = "movies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    release_year = Column(Integer, nullable=True)
    language = Column(String(10), nullable=False, default="en")
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    content_versions = relationship(
        "ContentVersionTable", back_populates="movie", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "ViewingSessionTable", back_populates="movie", cascade="all, delete-orphan"
    )


class ContentVersionTable(Base):
    """Versioned content asset and index state for a movie."""

    __tablename__ = "content_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False, default="srt")
    source_checksum = Column(String(64), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    processing_status = Column(String(20), nullable=False, default="queued", index=True)
    embedding_model = Column(String(100), nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Unique constraint per movie and version
    __table_args__ = (
        UniqueConstraint("movie_id", "version_number", name="uq_movie_version_number"),
    )

    # Relationships
    movie = relationship("MovieTable", back_populates="content_versions")
    chunks = relationship("SubtitleChunkTable", back_populates="content_version", cascade="all, delete-orphan")
    facts = relationship("StoryFactTable", back_populates="content_version", cascade="all, delete-orphan")


class SubtitleChunkTable(Base):
    """Timestamped dialogue chunk with embedding."""

    __tablename__ = "subtitle_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_version_id = Column(
        String(36), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal = Column(Integer, nullable=False)
    start_time_seconds = Column(Float, nullable=False, index=True)
    end_time_seconds = Column(Float, nullable=False, index=True)
    start_time_formatted = Column(String(20), nullable=False)
    end_time_formatted = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    speaker = Column(String(100), nullable=True)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("content_version_id", "ordinal", name="uq_version_chunk_ordinal"),
        CheckConstraint("start_time_seconds >= 0", name="chk_start_non_negative"),
        CheckConstraint("end_time_seconds >= start_time_seconds", name="chk_end_after_start"),
    )

    # Relationships
    content_version = relationship("ContentVersionTable", back_populates="chunks")


class StoryFactTable(Base):
    """Canon plot fact with first reveal boundary timestamp."""

    __tablename__ = "story_facts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_version_id = Column(
        String(36), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    fact = Column(Text, nullable=False)
    first_known_at_seconds = Column(Float, nullable=False, index=True)
    validation_status = Column(String(20), nullable=False, default="verified")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    content_version = relationship("ContentVersionTable", back_populates="facts")


class ViewingSessionTable(Base):
    """User viewing session with playback progress and spoiler state."""

    __tablename__ = "viewing_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, default="anonymous", index=True)
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    current_position_seconds = Column(Float, nullable=False, default=0.0, index=True)
    progress_source = Column(String(30), nullable=False, default="unknown")
    spoiler_mode = Column(String(10), nullable=False, default="safe")
    full_spoilers_confirmed = Column(Boolean, nullable=False, default=False)
    spoiler_confirmation_nonce = Column(String(64), nullable=True, index=True)
    spoiler_nonce_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("current_position_seconds >= 0", name="chk_session_position_non_negative"),
    )

    # Relationships
    movie = relationship("MovieTable", back_populates="sessions")
    questions = relationship("QuestionTable", back_populates="session", cascade="all, delete-orphan")


class QuestionTable(Base):
    """Question submitted during a session with grounded response."""

    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36), ForeignKey("viewing_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    request_id = Column(String(64), nullable=False, index=True)
    playback_position_seconds = Column(Float, nullable=False)
    spoiler_mode = Column(String(10), nullable=False)
    status = Column(String(40), nullable=False, default="answered")
    answer_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    session = relationship("ViewingSessionTable", back_populates="questions")
    sources = relationship("AnswerSourceTable", back_populates="question", cascade="all, delete-orphan")


class AnswerSourceTable(Base):
    """Citations linking a question answer to chunks or facts."""

    __tablename__ = "answer_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id = Column(
        String(36), ForeignKey("subtitle_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    story_fact_id = Column(
        String(36), ForeignKey("story_facts.id", ondelete="SET NULL"), nullable=True
    )
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    question = relationship("QuestionTable", back_populates="sources")


class AuditEventTable(Base):
    """Audit log for security and administrative actions."""

    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
