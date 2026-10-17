"""FastAPI dependency injection for database sessions, repositories, and viewer identity."""

from typing import AsyncGenerator
from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.infrastructure.database import async_session_factory
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    QuestionRepository,
    SubtitleChunkRepository,
    ViewingSessionRepository,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for request scope."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_current_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Extract authenticated or device viewer ID from request header.

    In 10-ft TV environment, device profiles provide X-User-ID or fall back
    to default local device profile.
    """
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    return "tv-viewer-primary"
