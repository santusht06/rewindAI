"""Integration tests for domain models, database schema, constraints, and repository layer.

Verifies BE-DATA-001..006, SRS-CAT-001, SRS-SES-001..004, SRS-SPO-001..004, AC-004, AC-009, AC-010.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.domain.models import (
    MovieStatus,
    ProgressSource,
    SpoilerMode,
    SubtitleChunkSchema,
)
from services.api.errors import ConflictError
from services.api.infrastructure.database import Base
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    SubtitleChunkRepository,
    ViewingSessionRepository,
)


@pytest_asyncio.fixture
async def test_db_session():
    """Create in-memory isolated async SQLite database for testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_movie_repository_crud(test_db_session: AsyncSession) -> None:
    """Verify movie creation, published listing, and status updates (SRS-CAT-001)."""
    repo = MovieRepository(test_db_session)
    await repo.create(title="Inception", release_year=2010, status=MovieStatus.PUBLISHED)
    movie2 = await repo.create(title="Interstellar", release_year=2014, status=MovieStatus.DRAFT)

    # list_published should return only movie1
    published = await repo.list_published()
    assert len(published) == 1
    assert published[0].title == "Inception"

    # Publish movie2
    updated = await repo.update_status(movie2.id, MovieStatus.PUBLISHED)
    assert updated.status == MovieStatus.PUBLISHED.value

    published_after = await repo.list_published()
    assert len(published_after) == 2


@pytest.mark.asyncio
async def test_content_version_atomic_publication(test_db_session: AsyncSession) -> None:
    """Verify staged indexing and atomic index version activation (SRS-ING-004, AC-018)."""
    movie_repo = MovieRepository(test_db_session)
    ver_repo = ContentVersionRepository(test_db_session)

    movie = await movie_repo.create(title="The Prestige", release_year=2006)

    # Create version 1 (staged)
    v1 = await ver_repo.create_version(movie_id=movie.id, source_checksum="hash_v1")
    assert not v1.is_active

    # Publish version 1
    await ver_repo.publish_version(v1.id)
    active_v1 = await ver_repo.get_active_version(movie.id)
    assert active_v1 is not None
    assert active_v1.id == v1.id
    assert active_v1.is_active

    # Create version 2 (staged replacement index)
    v2 = await ver_repo.create_version(movie_id=movie.id, source_checksum="hash_v2")
    assert not v2.is_active

    # Active version should still be v1 while v2 is staged (AC-013)
    current_active = await ver_repo.get_active_version(movie.id)
    assert current_active.id == v1.id

    # Now atomically publish version 2
    await ver_repo.publish_version(v2.id)

    # v2 is active and v1 is deactivated
    active_v2 = await ver_repo.get_active_version(movie.id)
    assert active_v2.id == v2.id
    assert active_v2.version_number == 2

    # Refresh v1
    v1_refreshed = await ver_repo.get_by_id(v1.id)
    assert not v1_refreshed.is_active


@pytest.mark.asyncio
async def test_subtitle_chunks_temporal_boundary_filter(test_db_session: AsyncSession) -> None:
    """Verify pre-retrieval temporal boundary filtering strictly blocks future chunks (SRS-QA-002, AC-004)."""
    movie_repo = MovieRepository(test_db_session)
    ver_repo = ContentVersionRepository(test_db_session)
    chunk_repo = SubtitleChunkRepository(test_db_session)

    movie = await movie_repo.create(title="Memento", release_year=2000)
    version = await ver_repo.create_version(movie_id=movie.id, source_checksum="hash_memento")

    # Add 4 sequential chunks across the timeline
    chunks = [
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 0,
            "start_time_seconds": 10.0,
            "end_time_seconds": 25.0,
            "start_time_formatted": "00:00:10",
            "end_time_formatted": "00:00:25",
            "text": "Opening scene clue about Leonard.",
        },
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 1,
            "start_time_seconds": 60.0,
            "end_time_seconds": 95.0,
            "start_time_formatted": "00:01:00",
            "end_time_formatted": "00:01:35",
            "text": "Meeting Teddy at the diner.",
        },
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 2,
            "start_time_seconds": 300.0,
            "end_time_seconds": 340.0,
            "start_time_formatted": "00:05:00",
            "end_time_formatted": "00:05:40",
            "text": "Mid-movie revelation about Sammy Jankis.",
        },
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 3,
            "start_time_seconds": 6000.0,
            "end_time_seconds": 6040.0,
            "start_time_formatted": "01:40:00",
            "end_time_formatted": "01:40:40",
            "text": "CRITICAL FINAL TWIST: Teddy reveals the truth.",
        },
    ]
    await chunk_repo.bulk_create(chunks)

    # 1. Viewer is at 2 minutes (120 seconds):
    # Should retrieve chunks 0 and 1, strictly excluding chunk 2 and twist chunk 3!
    permitted = await chunk_repo.get_chunks_within_boundary(
        content_version_id=version.id, max_end_time_seconds=120.0
    )
    assert len(permitted) == 2
    assert permitted[0].ordinal == 0
    assert permitted[1].ordinal == 1
    assert all("FINAL TWIST" not in c.text for c in permitted)

    # 2. Viewer at end of movie (7000s):
    all_chunks = await chunk_repo.get_chunks_within_boundary(
        content_version_id=version.id, max_end_time_seconds=7000.0
    )
    assert len(all_chunks) == 4


def test_subtitle_chunk_schema_invariant_reversed_timestamps() -> None:
    """Ensure SubtitleChunkSchema rejects invalid or reversed timestamps (AC-019)."""
    with pytest.raises(ValueError, match="end_time_seconds .* must be >= start_time_seconds"):
        SubtitleChunkSchema(
            content_version_id="ver-1",
            movie_id="mov-1",
            ordinal=1,
            start_time_seconds=100.0,
            end_time_seconds=50.0,  # Invalid: reversed!
            start_time_formatted="00:01:40",
            end_time_formatted="00:00:50",
            text="Invalid subtitle text",
        )


@pytest.mark.asyncio
async def test_viewing_session_spoiler_workflow(test_db_session: AsyncSession) -> None:
    """Verify session progress, single-use spoiler nonce, and expiration (SRS-SPO-004, AC-009, AC-010)."""
    movie_repo = MovieRepository(test_db_session)
    session_repo = ViewingSessionRepository(test_db_session)

    movie = await movie_repo.create(title="Shutter Island", release_year=2010)

    # Create new session: Defaults to safe mode (AC-001, AC-003)
    sess = await session_repo.create_session(
        movie_id=movie.id, user_id="user-42", current_position_seconds=300.0, progress_source=ProgressSource.MANUAL
    )
    assert sess.spoiler_mode == SpoilerMode.SAFE.value
    assert not sess.full_spoilers_confirmed

    # Update progress
    updated_sess = await session_repo.update_progress(sess.id, 900.0, ProgressSource.MANUAL)
    assert updated_sess.current_position_seconds == 900.0

    # Issue spoiler confirmation token (valid for 5 minutes)
    nonce = "secret-server-nonce-12345"
    expires = datetime.now(UTC) + timedelta(minutes=5)
    await session_repo.issue_spoiler_nonce(sess.id, nonce, expires)

    # Attempt confirmation with wrong token -> ConflictError (AC-010)
    with pytest.raises(ConflictError, match="Invalid or expired spoiler confirmation token"):
        await session_repo.confirm_spoiler_mode(sess.id, "wrong-nonce")

    # Confirm with correct token -> Full spoilers enabled (AC-009)
    confirmed_sess = await session_repo.confirm_spoiler_mode(sess.id, nonce)
    assert confirmed_sess.spoiler_mode == SpoilerMode.FULL.value
    assert confirmed_sess.full_spoilers_confirmed

    # Token should now be consumed (single-use)
    with pytest.raises(ConflictError):
        await session_repo.confirm_spoiler_mode(sess.id, nonce)

    # User resets back to safe mode
    reset_sess = await session_repo.reset_to_safe_mode(sess.id)
    assert reset_sess.spoiler_mode == SpoilerMode.SAFE.value
    assert not reset_sess.full_spoilers_confirmed


@pytest.mark.asyncio
async def test_audit_event_recording(test_db_session: AsyncSession) -> None:
    """Verify audit events are recorded with correlation IDs (SRS-ADM-002)."""
    audit_repo = AuditEventRepository(test_db_session)
    event = await audit_repo.record_event(
        actor="admin@rewind.ai",
        action="publish_index",
        target_type="content_version",
        target_id="ver-uuid-123",
        correlation_id="req-trace-456",
        metadata={"chunks_count": 145},
    )
    assert event.id is not None
    assert event.actor == "admin@rewind.ai"
    assert event.action == "publish_index"
    assert event.correlation_id == "req-trace-456"
