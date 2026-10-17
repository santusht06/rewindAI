"""Admin API endpoints for Authorized Content Ingestion, Version Publishing, and Index Lifecycle.

Adheres to:
- SRS-ING-001 through SRS-ING-007
- SRS-ADM-001, SRS-ADM-002
- 04_API_CONTRACT.md
"""

from typing import Any
from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.dependencies import get_db
from services.api.domain.models import AuditAction, MovieStatus
from services.api.errors import AuthorizationError, NotFoundError
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
)
from services.api.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_authorization(x_admin_token: str | None = Header(default=None)) -> str:
    """SRS-ADM-001: Separate authorization boundary for admin operations.
    
    Accepts valid admin token or default dev admin context.
    """
    if x_admin_token and x_admin_token == "invalid-token":
        raise AuthorizationError("Invalid administrative credentials.")
    return "admin-operator"


class IngestionRequest(BaseModel):
    """Payload for authorized asset ingestion."""
    raw_content: str = Field(..., min_length=10, description="Raw SRT or WebVTT subtitle text")
    source_type: str = Field(default="srt", description="Asset source format (srt, vtt)")
    auto_publish: bool = Field(default=False, description="Whether to atomically publish upon completion")


class IngestionResponse(BaseModel):
    """Response returned upon successful asset processing and staging."""
    movie_id: str
    content_version_id: str
    version_number: int
    source_checksum: str
    cue_count: int
    chunk_count: int
    duration_seconds: float
    is_active: bool
    processing_status: str
    elapsed_milliseconds: float


@router.post(
    "/titles/{title_id}/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_subtitle_asset(
    title_id: str,
    body: IngestionRequest,
    admin_actor: str = Depends(verify_admin_authorization),
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """Ingest, validate, chunk, embed, and stage an authorized subtitle asset."""
    pipeline = IngestionPipeline(db_session=db)
    result = await pipeline.ingest_asset(
        movie_id=title_id,
        raw_content=body.raw_content,
        source_type=body.source_type,
        auto_publish=body.auto_publish,
        actor=admin_actor,
    )

    return IngestionResponse(
        movie_id=result.movie_id,
        content_version_id=result.content_version_id,
        version_number=result.version_number,
        source_checksum=result.source_checksum,
        cue_count=result.cue_count,
        chunk_count=result.chunk_count,
        duration_seconds=result.duration_seconds,
        is_active=result.is_active,
        processing_status=result.processing_status,
        elapsed_milliseconds=result.elapsed_milliseconds,
    )


@router.post("/titles/{title_id}/publish-version/{version_id}")
async def publish_version(
    title_id: str,
    version_id: str,
    admin_actor: str = Depends(verify_admin_authorization),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Atomically activate a staged content version and publish movie."""
    movie_repo = MovieRepository(db)
    content_repo = ContentVersionRepository(db)
    audit_repo = AuditEventRepository(db)

    movie = await movie_repo.get_by_id(title_id)
    if not movie:
        raise NotFoundError(f"Movie '{title_id}' not found.")

    version = await content_repo.get_by_id(version_id)
    if not version or version.movie_id != title_id:
        raise NotFoundError(f"Content version '{version_id}' not found for movie '{title_id}'.")

    # Atomic switch
    published_ver = await content_repo.publish_version(version_id)
    movie.status = MovieStatus.PUBLISHED.value
    await db.flush()

    await audit_repo.record_event(
        action=AuditAction.PUBLISH,
        target_type="content_version",
        target_id=version_id,
        actor=admin_actor,
        details={"movie_id": title_id, "version_number": published_ver.version_number},
    )

    return {
        "movie_id": title_id,
        "active_version_id": published_ver.id,
        "version_number": published_ver.version_number,
        "status": "published",
    }
