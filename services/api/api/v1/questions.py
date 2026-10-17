"""API endpoint contract for Question submission and spoiler-gated Q&A.

Adheres to:
- SRS-SPO-001, SRS-SPO-002, SRS-SPO-004
- SRS-CAT-001, SRS-CAT-003
- AC-004, AC-007, AC-009, AC-010
- 04_API_CONTRACT.md
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.dependencies import get_current_user_id, get_db
from services.api.api.schemas import (
    CitationSchema,
    QuestionRequest,
    QuestionResponse,
)
from services.api.domain.models import (
    AuditEventAction,
    QuestionStatus,
    SpoilerMode,
)
from services.api.errors import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    QuestionRepository,
    SubtitleChunkRepository,
    ViewingSessionRepository,
)

router = APIRouter(prefix="/sessions", tags=["questions"])


@router.post("/{session_id}/questions", response_model=QuestionResponse)
async def ask_question(
    session_id: str,
    body: QuestionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """Submit a question within a viewing session.

    Enforces strict server-side boundary:
    1. Validates session existence and viewer identity.
    2. Validates question length and content.
    3. Respects server-controlled spoiler mode and current playback position.
    4. Future chunks (end_time_seconds > current_position_seconds) are filtered out pre-LLM in SAFE mode.
    """
    session_repo = ViewingSessionRepository(db)
    movie_repo = MovieRepository(db)
    content_repo = ContentVersionRepository(db)
    chunk_repo = SubtitleChunkRepository(db)
    question_repo = QuestionRepository(db)
    audit_repo = AuditEventRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to ask questions in this viewing session.")

    movie = await movie_repo.get_by_id(session.movie_id)
    if not movie:
        raise NotFoundError("Movie associated with this session was not found.")

    active_version = await content_repo.get_active_version(movie.id)
    now = datetime.now(timezone.utc)

    def get_spoiler_mode_str(mode: Any) -> str:
        return mode.value if hasattr(mode, "value") else str(mode)

    current_spoiler_str = get_spoiler_mode_str(session.spoiler_mode)
    is_safe_mode = current_spoiler_str == SpoilerMode.SAFE.value

    # If title has no active indexed version, return unsupported_title outcome per 04_API_CONTRACT
    if not active_version:
        return QuestionResponse(
            question_id=str(uuid.uuid4()),
            session_id=session.id,
            outcome="unsupported_title",
            answer="AI story companion is not currently indexed for this title.",
            citations=[],
            policy_state=current_spoiler_str,
            created_at=now,
        )

    # Record question in database for tracking
    question_record = await question_repo.create_question(
        session_id=session.id,
        movie_id=movie.id,
        user_id=user_id,
        question_text=body.question,
        playback_position_seconds=session.current_position_seconds,
        spoiler_mode_applied=current_spoiler_str,
        status=QuestionStatus.RECEIVED,
        request_id=body.client_request_id,
    )

    # In SAFE mode, strictly enforce pre-retrieval evidence boundary
    max_boundary = (
        session.current_position_seconds
        if is_safe_mode
        else movie.duration_seconds
    )

    # Detect explicit request for future spoilers while in SAFE mode
    lower_q = body.question.lower()
    future_keywords = ["what happens next", "how does it end", "who dies at the end", "spoiler", "future"]
    is_asking_future = any(k in lower_q for k in future_keywords)

    if is_safe_mode and is_asking_future:
        # Issue single-use spoiler confirmation nonce
        nonce = await session_repo.set_spoiler_confirmation_nonce(session.id)
        await question_repo.update_question_status(question_record.id, QuestionStatus.REJECTED_SPOILER)
        
        await audit_repo.record_event(
            action=AuditEventAction.QUESTION_SUBMIT,
            target_id=question_record.id,
            user_id=user_id,
            details={"outcome": "spoiler_confirmation_required", "position": session.current_position_seconds},
        )

        return QuestionResponse(
            question_id=question_record.id,
            session_id=session.id,
            outcome="spoiler_confirmation_required",
            answer=(
                f"Answering this question involves events that occur after your current playback "
                f"position ({session.current_position_seconds}s). To protect your story experience, "
                f"safe mode is enabled. Confirm below if you would like full spoilers."
            ),
            citations=[],
            confirmation_nonce=nonce,
            policy_state=current_spoiler_str,
            created_at=now,
        )

    # Query safe chunks within pre-retrieval boundary
    chunks = await chunk_repo.get_chunks_within_boundary(
        movie_id=movie.id,
        content_version_id=active_version.id,
        max_end_time_seconds=max_boundary,
    )

    if not chunks:
        # No evidence available up to this playback point
        await question_repo.update_question_status(question_record.id, QuestionStatus.INSUFFICIENT_EVIDENCE)
        return QuestionResponse(
            question_id=question_record.id,
            session_id=session.id,
            outcome="insufficient_evidence",
            answer="No dialogue or scene information has occurred yet at this playback timestamp.",
            citations=[],
            policy_state=current_spoiler_str,
            created_at=now,
        )

    # Match chunks for relevant keywords in query (baseline contract logic; full RAG in E5)
    matched_chunks = [c for c in chunks if any(word in c.text.lower() for word in lower_q.split() if len(word) > 3)]
    if not matched_chunks:
        matched_chunks = chunks[-2:]  # Most recent context up to current position

    citations = [
        CitationSchema(
            chunk_id=c.id,
            start_time_seconds=c.start_time_seconds,
            end_time_seconds=c.end_time_seconds,
            text=c.text,
            relevance_score=1.0,
        )
        for c in matched_chunks[:3]
    ]

    answer_text = (
        f"Based on the story up to {session.current_position_seconds}s: "
        f"{matched_chunks[0].text}"
    )

    await question_repo.update_question_status(
        question_id=question_record.id,
        status=QuestionStatus.ANSWERED,
        answer_text=answer_text,
    )

    for c in citations:
        await question_repo.link_citation(
            question_id=question_record.id,
            chunk_id=c.chunk_id,
            relevance_score=c.relevance_score,
        )

    return QuestionResponse(
        question_id=question_record.id,
        session_id=session.id,
        outcome="answered",
        answer=answer_text,
        citations=citations,
        policy_state=current_spoiler_str,
        created_at=now,
    )
