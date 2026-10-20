"""API endpoints for Viewing Session management, progress tracking, and spoiler authorization.

Adheres to:
- SRS-CAT-002, SRS-CAT-003
- SRS-SPO-001, SRS-SPO-002, SRS-SPO-004
- AC-004, AC-009, AC-010, AC-020
- 04_API_CONTRACT.md
"""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.dependencies import get_current_user_id, get_db
from services.api.api.schemas import (
    CreateSessionRequest,
    ProgressResponse,
    SessionResponse,
    SpoilerConfirmationRequest,
    SpoilerConfirmationResponse,
    TitleSummarySchema,
    UpdateProgressRequest,
)
from services.api.domain.models import (
    AuditEventAction,
    MovieStatus,
    ProgressSource,
    SpoilerMode,
)
from services.api.errors import (
    AppException,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    MovieRepository,
    ViewingSessionRepository,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _normalize_client_progress_source(source: ProgressSource) -> ProgressSource:
    """Prevent clients from asserting provenance that requires server verification."""
    if source in (ProgressSource.VERIFIED_INTEGRATION, ProgressSource.PARTNER_SYNC):
        return ProgressSource.MANUAL_SLIDER
    return source


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create an active viewing session for a published movie."""
    movie_repo = MovieRepository(db)
    session_repo = ViewingSessionRepository(db)
    audit_repo = AuditEventRepository(db)

    movie = await movie_repo.get_by_id(body.title_id)
    if not movie or movie.status != MovieStatus.PUBLISHED:
        raise NotFoundError(f"Title '{body.title_id}' is not available for viewing sessions.")

    # Validate initial position does not exceed movie duration
    initial_pos = min(body.position_seconds, movie.duration_seconds)

    source = _normalize_client_progress_source(body.source)

    session = await session_repo.create_session(
        user_id=user_id,
        movie_id=movie.id,
        initial_position=initial_pos,
        source=source,
    )

    await audit_repo.record_event(
        action=AuditEventAction.SESSION_START,
        target_id=session.id,
        user_id=user_id,
        details={
            "movie_id": movie.id,
            "initial_position": initial_pos,
            "source": source.value,
        },
    )

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        title=TitleSummarySchema(
            id=movie.id,
            display_title=movie.display_title,
            year=movie.year,
        ),
        current_position_seconds=session.current_position_seconds,
        progress_source=session.progress_source,
        spoiler_mode=session.spoiler_mode,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Retrieve current state of a viewing session."""
    session_repo = ViewingSessionRepository(db)
    movie_repo = MovieRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to access this viewing session.")

    movie = await movie_repo.get_by_id(session.movie_id)
    if not movie:
        raise NotFoundError(f"Associated movie for session '{session_id}' not found.")

    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        title=TitleSummarySchema(
            id=movie.id,
            display_title=movie.display_title,
            year=movie.year,
        ),
        current_position_seconds=session.current_position_seconds,
        progress_source=session.progress_source,
        spoiler_mode=session.spoiler_mode,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.patch("/{session_id}/progress", response_model=ProgressResponse)
async def update_progress(
    session_id: str,
    body: UpdateProgressRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ProgressResponse:
    """Update viewing session playback position.

    Enforces:
    - Bounded position within movie duration.
    - Untrusted clients cannot assert verified_integration or partner_sync provenance.
    - Session ownership check.
    """
    session_repo = ViewingSessionRepository(db)
    movie_repo = MovieRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to modify this viewing session.")

    movie = await movie_repo.get_by_id(session.movie_id)
    if not movie:
        raise NotFoundError("Movie associated with this session was not found.")

    if body.position_seconds > movie.duration_seconds:
        raise ValidationError(
            f"Position {body.position_seconds}s exceeds movie duration {movie.duration_seconds}s.",
            details={"max_allowed": movie.duration_seconds},
        )

    # Partner authentication is not implemented, so client-supplied provenance
    # cannot establish verification.
    source = _normalize_client_progress_source(body.source)

    updated_session = await session_repo.update_progress(
        session_id=session_id,
        position_seconds=body.position_seconds,
        source=source,
    )
    if not updated_session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    return ProgressResponse(
        session_id=updated_session.id,
        current_position_seconds=updated_session.current_position_seconds,
        progress_source=updated_session.progress_source,
        is_verified=False,
        spoiler_mode=updated_session.spoiler_mode,
        updated_at=updated_session.updated_at,
    )


@router.post("/{session_id}/spoiler-confirmation", response_model=SpoilerConfirmationResponse)
async def confirm_spoiler_mode(
    session_id: str,
    body: SpoilerConfirmationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SpoilerConfirmationResponse:
    """Consume single-use server nonce to authorize full spoiler mode.

    Adheres strictly to SRS-SPO-004, AC-009, AC-010.
    Never treats bare boolean claims as authorization.
    """
    session_repo = ViewingSessionRepository(db)
    audit_repo = AuditEventRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to alter spoiler policy for this session.")

    consumed = await session_repo.consume_spoiler_confirmation_nonce(
        session_id=session_id,
        nonce=body.confirmation_nonce,
    )

    if not consumed:
        # Invalid or expired nonce
        await audit_repo.record_event(
            action=AuditEventAction.SPOILER_OVERRIDE,
            target_id=session_id,
            user_id=user_id,
            details={"status": "rejected", "reason": "invalid_or_expired_nonce"},
        )
        raise AuthorizationError(
            "Invalid or expired spoiler confirmation token. Please request confirmation again."
        )

    # Log successful override audit event
    await audit_repo.record_event(
        action=AuditEventAction.SPOILER_OVERRIDE,
        target_id=session_id,
        user_id=user_id,
        details={"status": "confirmed", "mode": SpoilerMode.FULL.value},
    )

    refreshed_session = await session_repo.get_by_id(session_id)
    assert refreshed_session is not None

    return SpoilerConfirmationResponse(
        session_id=refreshed_session.id,
        spoiler_mode=refreshed_session.spoiler_mode,
        status="confirmed",
        updated_at=refreshed_session.updated_at,
    )


@router.post("/{session_id}/safe-mode", response_model=SessionResponse)
async def revert_to_safe_mode(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Immediately reset session spoiler policy back to SAFE mode."""
    session_repo = ViewingSessionRepository(db)
    movie_repo = MovieRepository(db)
    audit_repo = AuditEventRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to alter spoiler policy for this session.")

    updated_session = await session_repo.revert_to_safe_mode(session_id)
    if not updated_session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")

    await audit_repo.record_event(
        action=AuditEventAction.SAFE_MODE_REVERT,
        target_id=session_id,
        user_id=user_id,
        details={"mode": SpoilerMode.SAFE.value},
    )

    movie = await movie_repo.get_by_id(updated_session.movie_id)
    assert movie is not None

    return SessionResponse(
        session_id=updated_session.id,
        user_id=updated_session.user_id,
        title=TitleSummarySchema(
            id=movie.id,
            display_title=movie.display_title,
            year=movie.year,
        ),
        current_position_seconds=updated_session.current_position_seconds,
        progress_source=updated_session.progress_source,
        spoiler_mode=updated_session.spoiler_mode,
        created_at=updated_session.created_at,
        updated_at=updated_session.updated_at,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Close and delete a viewing session idempotently."""
    session_repo = ViewingSessionRepository(db)
    audit_repo = AuditEventRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        # Idempotent response
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to delete this viewing session.")

    await session_repo.delete_session(session_id)
    await audit_repo.record_event(
        action=AuditEventAction.SESSION_END,
        target_id=session_id,
        user_id=user_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
