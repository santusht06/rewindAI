"""Admin API endpoints for Authorized Content Ingestion, Version Publishing, and Index Lifecycle.

Adheres to:
- SRS-ING-001 through SRS-ING-007
- SRS-ADM-001, SRS-ADM-002
- 04_API_CONTRACT.md
"""

import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.dependencies import get_db
from services.api.api.schemas import CharacterFactCreateRequest, CharacterFactResponse
from services.api.config import settings
from services.api.domain.models import AuditAction, MovieStatus
from services.api.errors import AppException, AuthenticationError, AuthorizationError, NotFoundError
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    StoryFactRepository,
)
from services.api.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_authorization(x_admin_token: str | None = Header(default=None)) -> str:
    """Require a shared token for local/demo admin operations; fail closed in production."""
    if settings.is_production():
        raise AppException(
            code="ADMIN_AUTHORIZATION_NOT_CONFIGURED",
            message="Production administrative authorization is not configured.",
            status_code=503,
        )
    configured_token = (
        settings.admin_api_token.get_secret_value()
        if settings.admin_api_token
        else ""
    )
    if len(configured_token) < 32:
        raise AppException(
            code="ADMIN_AUTH_NOT_CONFIGURED",
            message="Administrative access is not configured.",
            status_code=503,
        )
    if not x_admin_token:
        raise AuthenticationError("Administrative credentials are required.")
    if not secrets.compare_digest(
        x_admin_token.encode("utf-8"),
        configured_token.encode("utf-8"),
    ):
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
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
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


@router.post("/titles/{title_id}/unpublish")
async def unpublish_title(
    title_id: str,
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Atomically deactivate active content versions and revoke published status (OPS-006, AC-016)."""
    movie_repo = MovieRepository(db)
    content_repo = ContentVersionRepository(db)
    audit_repo = AuditEventRepository(db)

    movie = await movie_repo.get_by_id(title_id)
    if not movie:
        raise NotFoundError(f"Movie '{title_id}' not found.")

    # Deactivate all active versions to prevent indexing/retrieval
    await content_repo.deactivate_all_versions(title_id)
    movie.status = MovieStatus.DRAFT.value
    await db.flush()

    await audit_repo.record_event(
        action=AuditAction.UNPUBLISH,
        target_type="movie",
        target_id=title_id,
        actor=admin_actor,
        details={"movie_id": title_id, "action": "rights_revocation_unpublish"},
    )

    return {
        "movie_id": title_id,
        "status": "draft",
        "message": f"Title '{title_id}' unpublished successfully.",
    }


@router.post(
    "/titles/{title_id}/character-facts",
    response_model=CharacterFactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character_fact(
    title_id: str,
    body: CharacterFactCreateRequest,
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CharacterFactResponse:
    """Attach a curated character fact and its first-reveal timestamp to the active index."""
    movie = await MovieRepository(db).get_by_id(title_id)
    if not movie:
        raise NotFoundError(f"Movie '{title_id}' not found.")
    version = await ContentVersionRepository(db).get_active_version(title_id)
    if not version:
        raise NotFoundError("Publish an active subtitle index before adding character facts.")
    if body.first_known_at_seconds > movie.duration_seconds:
        raise AppException(
            code="INVALID_REVEAL_TIME",
            message="The fact's reveal time cannot exceed the title duration.",
            status_code=422,
        )
    fact = await StoryFactRepository(db).create_character_fact(
        content_version_id=version.id,
        movie_id=title_id,
        character_name=body.character_name.strip(),
        fact=body.fact.strip(),
        relationship=body.relationship.strip() if body.relationship else None,
        first_known_at_seconds=body.first_known_at_seconds,
    )
    await AuditEventRepository(db).record_event(
        action=AuditAction.CHARACTER_FACT_CREATE,
        target_type="character_fact",
        target_id=fact.id,
        actor=admin_actor,
        details={
            "movie_id": title_id,
            "content_version_id": version.id,
            "first_known_at_seconds": fact.first_known_at_seconds,
        },
    )
    return CharacterFactResponse(
        fact=fact.fact,
        relationship=fact.relationship_description,
        first_known_at_seconds=int(fact.first_known_at_seconds),
    )


class MediaUploadRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_base64: str = Field(..., min_length=1)
    content_type: str = Field(default="video/mp4")
    supplied_srt_content: str | None = None


class MediaUploadResponse(BaseModel):
    job_id: str
    movie_id: str
    stage: str
    message: str


class ProcessingJobResponse(BaseModel):
    id: str
    movie_id: str
    stage: str
    attempts: int
    max_attempts: int
    is_retryable: bool
    is_playback_ready: bool
    is_ai_ready: bool
    error_code: str | None = None
    error_message: str | None = None


@router.post(
    "/movies/{title_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Media Asset and Start Processing Job",
)
async def upload_movie_media(
    title_id: str,
    body: MediaUploadRequest,
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MediaUploadResponse:
    """Upload video binary and begin asynchronous media pipeline."""
    import base64
    from services.api.media.pipeline import MediaPipeline

    try:
        file_bytes = base64.b64decode(body.file_base64)
    except Exception as exc:
        raise AppException(code="INVALID_BASE64", message=f"Failed to decode base64: {exc}", status_code=400)

    pipeline = MediaPipeline(db)
    job_id = await pipeline.create_upload_job(
        movie_id=title_id,
        file_name=body.file_name,
        file_bytes=file_bytes,
        content_type=body.content_type,
        supplied_srt_content=body.supplied_srt_content,
    )

    # Trigger processing execution immediately
    await pipeline.execute_job(job_id=job_id, supplied_srt_content=body.supplied_srt_content)

    return MediaUploadResponse(
        job_id=job_id,
        movie_id=title_id,
        stage="processing",
        message="Media uploaded and processing initiated.",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ProcessingJobResponse,
    summary="Get Media Processing Job Status",
)
async def get_processing_job_status(
    job_id: str,
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProcessingJobResponse:
    """Inspect durable media processing job status and readiness gates."""
    from services.api.infrastructure.repositories import ProcessingJobRepository

    job = await ProcessingJobRepository(db).get_by_id(job_id)
    if not job:
        raise NotFoundError(f"ProcessingJob '{job_id}' not found.")

    return ProcessingJobResponse(
        id=job.id,
        movie_id=job.movie_id,
        stage=job.stage,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        is_retryable=job.is_retryable,
        is_playback_ready=job.is_playback_ready,
        is_ai_ready=job.is_ai_ready,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ProcessingJobResponse,
    summary="Retry a Failed Media Processing Job",
)
async def retry_processing_job(
    job_id: str,
    admin_actor: Annotated[str, Depends(verify_admin_authorization)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProcessingJobResponse:
    """Retry an existing processing job (AT-05)."""
    from services.api.infrastructure.repositories import ProcessingJobRepository
    from services.api.media.pipeline import MediaPipeline

    job_repo = ProcessingJobRepository(db)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise NotFoundError(f"ProcessingJob '{job_id}' not found.")
    if not job.is_retryable:
        raise AppException(code="NON_RETRYABLE_JOB", message="This job is not retryable.", status_code=400)

    pipeline = MediaPipeline(db)
    await pipeline.execute_job(job_id=job_id)

    updated_job = await job_repo.get_by_id(job_id)
    assert updated_job is not None
    return ProcessingJobResponse(
        id=updated_job.id,
        movie_id=updated_job.movie_id,
        stage=updated_job.stage,
        attempts=updated_job.attempts,
        max_attempts=updated_job.max_attempts,
        is_retryable=updated_job.is_retryable,
        is_playback_ready=updated_job.is_playback_ready,
        is_ai_ready=updated_job.is_ai_ready,
        error_code=updated_job.error_code,
        error_message=updated_job.error_message,
    )

