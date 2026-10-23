"""Database connection management and async session provider.

Implements NFR-SEC-002 (parameterized queries, safe ORM) and 03_DOMAIN_MODEL_AND_DATABASE.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from services.api.config import settings


class Base(DeclarativeBase):
    """Base class for typed SQLAlchemy ORM models."""


def get_engine(db_url: str | None = None) -> AsyncEngine:
    """Create configured async SQLAlchemy engine."""
    url = db_url or settings.database_url
    # Configure SQLite or PostgreSQL specific arguments
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30.0

    eng = create_async_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )

    if url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(eng.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return eng


# Engine & Sessionmaker instances
engine = get_engine()
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated transactional async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables(target_engine: AsyncEngine | None = None) -> None:
    """Helper to create all registered tables (primarily for tests and local dev)."""
    eng = target_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables(target_engine: AsyncEngine | None = None) -> None:
    """Helper to drop all registered tables (primarily for test tear-down)."""
    eng = target_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
