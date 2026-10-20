"""FastAPI dependency injection for database sessions, repositories, and viewer identity."""

from collections.abc import AsyncGenerator

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.config import settings
from services.api.errors import AppException
from services.api.infrastructure.database import async_session_factory


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
    """Resolve a local/demo viewer ID; production access stays disabled without auth.

    In 10-ft TV environment, device profiles provide X-User-ID or fall back
    to a local demo profile. Production identity is disabled until an identity
    provider is selected and its credentials are verified server-side.
    """
    if settings.is_production():
        raise AppException(
            code="AUTHENTICATION_NOT_CONFIGURED",
            message="Viewer authentication is not configured.",
            status_code=503,
        )
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    return "tv-viewer-primary"
