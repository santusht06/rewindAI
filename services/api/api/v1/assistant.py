"""API endpoints for cross-application AI assistant capabilities and provider registry.

Implements requirements from 17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md:
- Provider capability querying
- Presentation mode inspection
- Context resolution with explicit provenance
"""

from typing import Annotated
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.dependencies import get_current_user_id, get_db
from services.api.assistant.contracts import (
    AssistantEntryPoint,
    AssistantPresentationMode,
    PlaybackContext,
    StreamingProviderInfo,
)
from services.api.assistant.registry import provider_registry
from services.api.assistant.adapters import StandardPlaybackContextAdapter
from services.api.domain.models import ProgressSource
from services.api.errors import AuthorizationError, NotFoundError
from services.api.infrastructure.repositories import (
    MovieRepository,
    ViewingSessionRepository,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])
ViewerId = Annotated[str, Depends(get_current_user_id)]
Database = Annotated[AsyncSession, Depends(get_db)]


class ProviderListResponse(BaseModel):
    """List of registered streaming providers and verified capabilities."""

    providers: list[StreamingProviderInfo]
    total: int


class PresentationModesResponse(BaseModel):
    """Supported presentation surfaces and invocation entry points on target platform."""

    target_os: str = Field(default="Dual-Target (Fire OS & Vega OS)")
    supported_modes: list[AssistantPresentationMode]
    supported_entry_points: list[AssistantEntryPoint]
    default_mode: AssistantPresentationMode = AssistantPresentationMode.SIDE_PANEL_OVERLAY


class ResolveContextRequest(BaseModel):
    """Request to bind or update assistant playback context for a streaming session."""

    provider_id: str = Field(..., description="Target streaming provider (e.g. netflix, prime_video)")
    position_seconds: int = Field(..., ge=0, description="Active playback position in seconds")
    source: ProgressSource = Field(default=ProgressSource.MANUAL_SLIDER)


@router.get("/providers", response_model=ProviderListResponse, summary="List Streaming Providers & Capabilities")
async def list_streaming_providers() -> ProviderListResponse:
    """Return all supported third-party streaming providers with their verified capabilities.
    
    Adheres to requirement 17: Transparently records which capabilities are VERIFIED,
    PARTIAL, or UNAVAILABLE due to OS container sandboxing.
    """
    providers = provider_registry.list_providers()
    return ProviderListResponse(providers=providers, total=len(providers))


@router.get("/providers/{provider_id}", response_model=StreamingProviderInfo, summary="Get Provider Capability Details")
async def get_provider_details(provider_id: str) -> StreamingProviderInfo:
    """Retrieve capability status, sandbox notes, and approved fallbacks for a specific provider."""
    provider = provider_registry.get_provider(provider_id)
    if not provider:
        raise NotFoundError(f"Streaming provider '{provider_id}' is not registered.")
    return provider


@router.get("/modes", response_model=PresentationModesResponse, summary="Get Presentation & Invocation Modes")
async def get_presentation_modes() -> PresentationModesResponse:
    """Return presentation modes (Side Panel, Modal Overlay, Companion Device) available on Fire TV & Vega OS."""
    return PresentationModesResponse(
        target_os="Amazon Fire OS & Vega OS W3C Runtime",
        supported_modes=[
            AssistantPresentationMode.SIDE_PANEL_OVERLAY,
            AssistantPresentationMode.MODAL_OVERLAY,
            AssistantPresentationMode.FOREGROUND_COMPANION,
            AssistantPresentationMode.COMPANION_DEVICE,
        ],
        supported_entry_points=[
            AssistantEntryPoint.VOICE_COMMAND,
            AssistantEntryPoint.REMOTE_SHORTCUT,
            AssistantEntryPoint.COMPANION_PAIRED,
            AssistantEntryPoint.MANUAL_LAUNCHER,
        ],
        default_mode=AssistantPresentationMode.SIDE_PANEL_OVERLAY,
    )


@router.get("/sessions/{session_id}/context", response_model=PlaybackContext, summary="Get Active Assistant Playback Context")
async def get_session_context(
    session_id: str,
    user_id: ViewerId,
    db: Database,
) -> PlaybackContext:
    """Resolve current playback context and provenance for an active assistant session."""
    session_repo = ViewingSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")
    if session.user_id != user_id:
        raise AuthorizationError("Access denied to this viewing session.")

    adapter = StandardPlaybackContextAdapter(
        session_repo=session_repo,
        movie_repo=MovieRepository(db),
    )
    return await adapter.get_current_context(session_id)


@router.post(
    "/sessions/{session_id}/context",
    response_model=PlaybackContext,
    status_code=status.HTTP_200_OK,
    summary="Update Assistant Playback Context",
)
async def update_session_context(
    session_id: str,
    body: ResolveContextRequest,
    user_id: ViewerId,
    db: Database,
) -> PlaybackContext:
    """Update playback context from a specific streaming provider with provenance tracking."""
    session_repo = ViewingSessionRepository(db)
    movie_repo = MovieRepository(db)

    session = await session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")
    if session.user_id != user_id:
        raise AuthorizationError("Access denied to this viewing session.")

    movie = await movie_repo.get_by_id(session.movie_id)
    if not movie:
        raise NotFoundError(f"Movie '{session.movie_id}' not found.")

    # Bound position within movie duration
    bounded_pos = min(body.position_seconds, movie.duration_seconds or body.position_seconds)

    # Normalize progress source per anti-spoofing policy
    normalized_source = body.source
    if normalized_source in (ProgressSource.VERIFIED_INTEGRATION, ProgressSource.PARTNER_SYNC):
        normalized_source = ProgressSource.MANUAL_SLIDER

    updated_session = await session_repo.update_progress(
        session_id=session_id,
        position_seconds=bounded_pos,
        source=normalized_source,
    )

    provider = provider_registry.get_provider(body.provider_id)
    provider_name = provider.name if provider else body.provider_id.title()

    provenance = f"User confirmed playback offset in {provider_name}"
    if body.source == ProgressSource.VOICE_CUE:
        provenance = f"Voice cue sync for {provider_name}"
    elif body.source == ProgressSource.MANUAL:
        provenance = f"Manual timestamp entry for {provider_name}"


    duration = movie.duration_seconds if movie.duration_seconds and movie.duration_seconds > 0 else 7200

    return PlaybackContext(
        provider_id=body.provider_id,
        title_id=movie.id,
        display_title=movie.title,
        current_position_seconds=updated_session.current_position_seconds,
        duration_seconds=duration,
        language=movie.language or "en",
        is_verified=False,
        provenance_note=provenance,
    )
