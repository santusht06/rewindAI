"""Pydantic schemas for API request and response contracts.

Adheres strictly to Rewind Complete Documentation Package:
- 04_API_CONTRACT.md
- SRS-CAT-001, SRS-CAT-003
- SRS-SPO-001, SRS-SPO-004
- AC-004, AC-009, AC-010, AC-020
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.api.domain.models import (
    MovieStatus,
    ProgressSource,
    SpoilerMode,
)

# ==========================================
# Titles & Catalog Schemas
# ==========================================

class TitleSummarySchema(BaseModel):
    """Compact summary of a movie title."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_title: str
    year: int | None = None


class TitleListItemSchema(BaseModel):
    """Catalog list item with viewer-safe indexing status."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_title: str
    year: int | None = None
    duration_seconds: int
    availability: str = Field(default="available", description="Playback availability state")
    index_status: str = Field(default="ready", description="Safe index status: ready, indexing, or unavailable")
    has_active_index: bool = True
    stream_url: str | None = None
    is_playback_ready: bool = True


class TitleListResponse(BaseModel):
    """Bounded paginated catalog response."""
    items: list[TitleListItemSchema]
    total: int
    next_cursor: str | None = None


class TitleDetailResponse(BaseModel):
    """Detailed metadata for a single title."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_title: str
    year: int | None = None
    duration_seconds: int
    status: MovieStatus
    questions_available: bool = True
    supported_locales: list[str] = Field(default_factory=lambda: ["en"])
    stream_url: str | None = None
    is_playback_ready: bool = True


# ==========================================
# Viewing Sessions & Progress Schemas
# ==========================================

class CreateSessionRequest(BaseModel):
    """Request to create an active viewing session."""
    title_id: str = Field(..., description="ID of the movie title to view")
    locale: str = Field(default="en", max_length=10)
    position_seconds: int = Field(default=0, ge=0, description="Initial playback offset")
    source: ProgressSource = Field(
        default=ProgressSource.MANUAL_SLIDER,
        description="Client source; server-only provenance values are normalized.",
    )


class SessionResponse(BaseModel):
    """Response returned upon session creation or state retrieval."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    user_id: str
    title: TitleSummarySchema
    current_position_seconds: int
    progress_source: ProgressSource
    spoiler_mode: SpoilerMode
    created_at: datetime
    updated_at: datetime


class UpdateProgressRequest(BaseModel):
    """Request to update playback position.

    Clients cannot self-assert verified_integration or partner_sync without
    server-side cryptographic verification or partner validation.
    """
    position_seconds: int | None = Field(default=None, ge=0, description="Playback position in integer seconds")
    current_position_seconds: int | None = Field(default=None, ge=0)
    source: ProgressSource = Field(default=ProgressSource.MANUAL_SLIDER)
    duration_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def normalize_position(self) -> "UpdateProgressRequest":
        if self.position_seconds is None and self.current_position_seconds is not None:
            self.position_seconds = self.current_position_seconds
        elif self.position_seconds is None:
            self.position_seconds = 0
        return self


class ProgressResponse(BaseModel):
    """Response containing validated and normalized progress."""
    session_id: str
    current_position_seconds: int
    progress_source: ProgressSource
    is_verified: bool
    spoiler_mode: SpoilerMode
    updated_at: datetime


class SpoilerConfirmationRequest(BaseModel):
    """Request to authorize full spoiler mode using a single-use server nonce."""
    confirmation_nonce: str = Field(..., min_length=8, description="Cryptographic single-use nonce issued by server")


class SpoilerConfirmationResponse(BaseModel):
    """Response after consuming single-use spoiler nonce."""
    session_id: str
    spoiler_mode: SpoilerMode
    status: Literal["confirmed"] = "confirmed"
    updated_at: datetime


# ==========================================
# Q&A & Evidence Schemas
# ==========================================

class CitationSchema(BaseModel):
    """Viewer-safe evidence reference grounded in subtitle chunks."""
    chunk_id: str
    start_time_seconds: int
    end_time_seconds: int
    text: str
    relevance_score: float = 1.0


QuestionOutcomeType = Literal[
    "answered",
    "needs_clarification",
    "insufficient_evidence",
    "spoiler_confirmation_required",
    "unsupported_title",
]


class QuestionRequest(BaseModel):
    """Question submission request.

    Invariants:
    - Client CANNOT specify spoiler policy bypass.
    - Question length is strictly bounded (max 500 chars).
    """
    question: str = Field(..., min_length=2, max_length=500, description="User question about the story")
    client_request_id: str | None = Field(default=None, max_length=128)
    locale: str = Field(default="en", max_length=10)


class QuestionResponse(BaseModel):
    """Typed Q&A response contract per 04_API_CONTRACT."""
    question_id: str
    session_id: str
    outcome: QuestionOutcomeType
    answer: str | None = None
    citations: list[CitationSchema] = Field(default_factory=list)
    clarification_prompt: str | None = None
    confirmation_nonce: str | None = None
    policy_state: str = "safe"
    created_at: datetime


class SubtitleLineSchema(BaseModel):
    """A subtitle passage available within the viewer's server-enforced story boundary."""

    cue_id: str
    start_time_seconds: int
    end_time_seconds: int
    text: str


class SubtitleLineSearchResponse(BaseModel):
    items: list[SubtitleLineSchema]


class TranslationRequest(BaseModel):
    """Select an indexed subtitle passage and request a bounded translation."""

    cue_id: str = Field(..., min_length=1, max_length=36)
    target_locale: Literal["en", "es", "fr", "hi", "ja"]
    explain_context: bool = True


class TranslationCitationSchema(BaseModel):
    cue_id: str
    start_time_seconds: int
    end_time_seconds: int
    text: str


class TranslationResponse(BaseModel):
    outcome: Literal["translated", "insufficient_evidence"]
    original_text: str
    target_locale: str
    translation: str | None = None
    contextual_explanation: str | None = None
    citation: TranslationCitationSchema
    message: str | None = None


class CharacterFactCreateRequest(BaseModel):
    """Curated, authorized character information with a first-reveal boundary."""

    character_name: str = Field(..., min_length=1, max_length=120)
    fact: str = Field(..., min_length=1, max_length=1000)
    relationship: str | None = Field(default=None, max_length=240)
    first_known_at_seconds: int = Field(..., ge=0)

    @field_validator("character_name", "fact")
    @classmethod
    def validate_non_whitespace(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized


class CharacterFactResponse(BaseModel):
    fact: str
    relationship: str | None = None
    first_known_at_seconds: int


class CharacterCardSchema(BaseModel):
    character_name: str
    facts: list[CharacterFactResponse]


class CharacterCardsResponse(BaseModel):
    items: list[CharacterCardSchema]
