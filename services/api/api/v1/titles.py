"""API endpoints for Title Catalog discovery and metadata lookup.

Adheres to:
- SRS-CAT-001 (Catalog of supported titles)
- SRS-CAT-003 (Metadata lookup)
- 04_API_CONTRACT.md (Bounded pagination, safe index status)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.dependencies import get_db
from services.api.api.schemas import (
    TitleDetailResponse,
    TitleListItemSchema,
    TitleListResponse,
)
from services.api.domain.models import MovieStatus
from services.api.errors import NotFoundError
from services.api.infrastructure.repositories import ContentVersionRepository, MovieRepository

router = APIRouter(prefix="/titles", tags=["titles"])


@router.get("", response_model=TitleListResponse)
async def list_titles(
    query: str | None = Query(default=None, max_length=100, description="Optional search term"),
    limit: int = Query(default=20, ge=1, le=50, description="Page limit (max 50)"),
    cursor: str | None = Query(default=None, description="Cursor for pagination"),
    db: AsyncSession = Depends(get_db),
) -> TitleListResponse:
    """List published titles available for viewing and Q&A."""
    movie_repo = MovieRepository(db)
    content_repo = ContentVersionRepository(db)

    movies = await movie_repo.list_published(limit=limit, query=query)
    
    items: list[TitleListItemSchema] = []
    for m in movies:
        active_version = await content_repo.get_active_version(m.id)
        has_active = active_version is not None
        index_status = "ready" if has_active else "unavailable"

        items.append(
            TitleListItemSchema(
                id=m.id,
                display_title=m.display_title,
                year=m.year,
                duration_seconds=m.duration_seconds,
                availability="available" if m.status == MovieStatus.PUBLISHED else "unavailable",
                index_status=index_status,
                has_active_index=has_active,
            )
        )

    return TitleListResponse(
        items=items,
        total=len(items),
        next_cursor=None,
    )


@router.get("/{title_id}", response_model=TitleDetailResponse)
async def get_title(
    title_id: str,
    db: AsyncSession = Depends(get_db),
) -> TitleDetailResponse:
    """Retrieve title details and Q&A availability.
    
    Does not expose sensitive internal storage paths or operator data.
    """
    movie_repo = MovieRepository(db)
    content_repo = ContentVersionRepository(db)

    movie = await movie_repo.get_by_id(title_id)
    if not movie or movie.status != MovieStatus.PUBLISHED:
        raise NotFoundError(f"Title '{title_id}' was not found or is not currently available.")

    active_version = await content_repo.get_active_version(movie.id)
    questions_available = active_version is not None

    return TitleDetailResponse(
        id=movie.id,
        display_title=movie.display_title,
        year=movie.year,
        duration_seconds=movie.duration_seconds,
        status=movie.status,
        questions_available=questions_available,
        supported_locales=["en", "es", "fr", "hi", "ja"],
    )
