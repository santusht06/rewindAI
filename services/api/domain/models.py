"""Domain models, value objects, and status enumerations for Rewind.

Implements SRS-CAT-001, SRS-SES-001..004, SRS-SPO-001..004, 03_DOMAIN_MODEL_AND_DATABASE.
"""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, Field, model_validator


class MovieStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNLISTED = "unlisted"


class ContentProcessingStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    STAGED = "staged"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressSource(str, Enum):
    VERIFIED_INTEGRATION = "verified_integration"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class SpoilerMode(str, Enum):
    SAFE = "safe"
    FULL = "full"


class QuestionStatus(str, Enum):
    ANSWERED = "answered"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    SPOILER_CONFIRMATION_REQUIRED = "spoiler_confirmation_required"
    UNSUPPORTED_TITLE = "unsupported_title"
    FAILED = "failed"


class FactValidationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"


class AuditAction(str, Enum):
    PUBLISH = "publish"
    UNPUBLISH = "unpublish"
    REINDEX = "reindex"
    PURGE = "purge"
    SPOILER_CONFIRMED = "spoiler_confirmed"


# Pydantic Domain Schemas for Transfer and Validation


class MovieSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, max_length=255)
    release_year: int | None = Field(default=None, ge=1880, le=2100)
    language: str = Field(default="en", max_length=10)
    status: MovieStatus = MovieStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentVersionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    movie_id: str
    source_type: str = Field(default="srt")
    source_checksum: str = Field(..., min_length=16)
    version_number: int = Field(default=1, ge=1)
    processing_status: ContentProcessingStatus = ContentProcessingStatus.QUEUED
    embedding_model: str | None = None
    chunk_count: int = Field(default=0, ge=0)
    is_active: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SubtitleChunkSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_version_id: str
    movie_id: str
    ordinal: int = Field(..., ge=0)
    start_time_seconds: float = Field(..., ge=0.0)
    end_time_seconds: float = Field(..., ge=0.0)
    start_time_formatted: str
    end_time_formatted: str
    text: str = Field(..., min_length=1)
    speaker: str | None = None
    embedding: list[float] | None = None

    @model_validator(mode="after")
    def validate_time_order(self) -> "SubtitleChunkSchema":
        if self.end_time_seconds < self.start_time_seconds:
            raise ValueError(
                f"end_time_seconds ({self.end_time_seconds}) must be >= start_time_seconds ({self.start_time_seconds})"
            )
        return self


class ViewingSessionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(default="anonymous")
    movie_id: str
    current_position_seconds: float = Field(default=0.0, ge=0.0)
    progress_source: ProgressSource = ProgressSource.UNKNOWN
    spoiler_mode: SpoilerMode = SpoilerMode.SAFE
    full_spoilers_confirmed: bool = False
    spoiler_confirmation_nonce: str | None = None
    spoiler_nonce_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_spoiler_permitted(self) -> bool:
        """Enforces that full spoiler mode requires verified confirmation."""
        return self.spoiler_mode == SpoilerMode.FULL and self.full_spoilers_confirmed


class QuestionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    movie_id: str
    question_text: str = Field(..., min_length=1, max_length=1000)
    request_id: str
    playback_position_seconds: float = Field(..., ge=0.0)
    spoiler_mode: SpoilerMode = SpoilerMode.SAFE
    status: QuestionStatus = QuestionStatus.NEEDS_CLARIFICATION
    answer_text: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CitationSchema(BaseModel):
    chunk_id: str
    start_time_seconds: float
    end_time_seconds: float
    start_time_formatted: str
    end_time_formatted: str
    text_snippet: str
    speaker: str | None = None
    relevance_score: float | None = None
