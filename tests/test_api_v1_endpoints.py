"""Integration and contract tests for Rewind API v1 endpoints.

Tests:
- GET /api/v1/titles (SRS-CAT-001)
- GET /api/v1/titles/{id} (SRS-CAT-003)
- POST /api/v1/sessions (SRS-SPO-001)
- GET /api/v1/sessions/{id}
- PATCH /api/v1/sessions/{id}/progress (SRS-SPO-001, AC-004)
- POST /api/v1/sessions/{id}/spoiler-confirmation (SRS-SPO-004, AC-009, AC-010)
- POST /api/v1/sessions/{id}/safe-mode
- DELETE /api/v1/sessions/{id}
- POST /api/v1/sessions/{id}/questions (AC-004, AC-007, 04_API_CONTRACT)
- OpenAPI schema generation check (BE-API-008)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.api.dependencies import get_db
from services.api.domain.models import (
    ContentProcessingStatus,
    MovieStatus,
    ProgressSource,
    SpoilerMode,
)
from services.api.infrastructure.repositories import (
    ContentVersionRepository,
    MovieRepository,
    SubtitleChunkRepository,
)
from services.api.infrastructure.tables import Base
from services.api.main import create_app


@pytest_asyncio.fixture
async def test_db_session():
    """In-memory SQLite async database engine for isolated API testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(test_db_session: AsyncSession):
    """Async HTTP client configured with overridden DB dependency."""
    app = create_app()

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_openapi_schema_generation(api_client: AsyncClient):
    """BE-API-008: Verify OpenAPI documentation is valid and contains API v1 routes."""
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/api/v1/titles" in schema["paths"]
    assert "/api/v1/sessions" in schema["paths"]
    assert "/api/v1/sessions/{session_id}/progress" in schema["paths"]
    assert "/api/v1/sessions/{session_id}/spoiler-confirmation" in schema["paths"]
    assert "/api/v1/sessions/{session_id}/questions" in schema["paths"]


@pytest.mark.asyncio
async def test_titles_catalog_empty_and_populated(
    api_client: AsyncClient,
    test_db_session: AsyncSession,
):
    """SRS-CAT-001: List titles and verify visibility rules."""
    # 1. Empty catalog
    res = await api_client.get("/api/v1/titles")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0

    # 2. Seed a published title and a draft title
    movie_repo = MovieRepository(test_db_session)
    content_repo = ContentVersionRepository(test_db_session)

    m1 = await movie_repo.create_movie(
        title_id="test-movie-1",
        display_title="The Quantum Paradox",
        year=2024,
        duration_seconds=7200,
        status=MovieStatus.PUBLISHED,
    )
    await movie_repo.create_movie(
        title_id="test-movie-draft",
        display_title="Unreleased Secret",
        year=2025,
        duration_seconds=5000,
        status=MovieStatus.DRAFT,
    )

    v1 = await content_repo.create_version(
        movie_id=m1.id,
        version_tag="v1.0.0",
        source_hash="hash1",
        status=ContentProcessingStatus.COMPLETED,
    )
    await content_repo.publish_version(v1.id)

    # 3. Query published titles
    res = await api_client.get("/api/v1/titles")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "test-movie-1"
    assert data["items"][0]["display_title"] == "The Quantum Paradox"
    assert data["items"][0]["index_status"] == "ready"
    assert data["items"][0]["has_active_index"] is True


@pytest.mark.asyncio
async def test_title_detail_success_and_not_found(
    api_client: AsyncClient,
    test_db_session: AsyncSession,
):
    """SRS-CAT-003: Retrieve title detail and handle non-existent title."""
    movie_repo = MovieRepository(test_db_session)
    await movie_repo.create_movie(
        title_id="inception-test",
        display_title="Inception",
        year=2010,
        duration_seconds=8880,
        status=MovieStatus.PUBLISHED,
    )

    # Success case
    res = await api_client.get("/api/v1/titles/inception-test")
    assert res.status_code == 200
    data = res.json()
    assert data["display_title"] == "Inception"
    assert data["year"] == 2010
    assert data["duration_seconds"] == 8880

    # 404 for unknown title
    res_404 = await api_client.get("/api/v1/titles/non-existent-id")
    assert res_404.status_code == 404
    error_env = res_404.json()
    assert error_env["code"] == "NOT_FOUND"
    assert "not found" in error_env["message"].lower()


@pytest.mark.asyncio
async def test_session_lifecycle_and_spoiler_controls(
    api_client: AsyncClient,
    test_db_session: AsyncSession,
):
    """SRS-SPO-001, SRS-SPO-004, AC-009, AC-010: Session lifecycle with spoiler nonce."""
    movie_repo = MovieRepository(test_db_session)
    movie = await movie_repo.create_movie(
        title_id="session-movie",
        display_title="Interstellar Journey",
        year=2014,
        duration_seconds=10000,
        status=MovieStatus.PUBLISHED,
    )

    headers = {"X-User-ID": "viewer-alice"}

    # 1. Create Session
    create_res = await api_client.post(
        "/api/v1/sessions",
        json={"title_id": movie.id, "position_seconds": 120},
        headers=headers,
    )
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["session_id"]
    assert session_data["spoiler_mode"] == "safe"
    assert session_data["current_position_seconds"] == 120
    assert session_data["progress_source"] == "manual_slider"

    # 2. Get Session State
    get_res = await api_client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id

    # 3. Ownership enforcement: different viewer gets 403 Forbidden
    other_viewer_headers = {"X-User-ID": "viewer-bob"}
    forbidden_res = await api_client.get(f"/api/v1/sessions/{session_id}", headers=other_viewer_headers)
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["code"] == "FORBIDDEN"

    # 4. Update Progress
    patch_res = await api_client.patch(
        f"/api/v1/sessions/{session_id}/progress",
        json={"position_seconds": 3600, "source": "manual_slider"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["current_position_seconds"] == 3600

    # 5. Position out of bounds fails validation
    invalid_pos_res = await api_client.patch(
        f"/api/v1/sessions/{session_id}/progress",
        json={"position_seconds": 999999, "source": "manual_slider"},
        headers=headers,
    )
    assert invalid_pos_res.status_code == 422
    assert "exceeds movie duration" in invalid_pos_res.json()["message"]

    # 6. Untrusted client self-asserting verified_integration is normalized
    untrusted_res = await api_client.patch(
        f"/api/v1/sessions/{session_id}/progress",
        json={"position_seconds": 4000, "source": "verified_integration"},
        headers=headers,
    )
    assert untrusted_res.status_code == 200
    # Normalized to manual slider, is_verified is False
    assert untrusted_res.json()["progress_source"] == "manual_slider"
    assert untrusted_res.json()["is_verified"] is False


@pytest.mark.asyncio
async def test_single_use_spoiler_nonce_authorization(
    api_client: AsyncClient,
    test_db_session: AsyncSession,
):
    """SRS-SPO-004, AC-010: Verify single-use nonce consumption and safe-mode revert."""
    movie_repo = MovieRepository(test_db_session)
    content_repo = ContentVersionRepository(test_db_session)
    movie = await movie_repo.create_movie(
        title_id="spoiler-film",
        display_title="Mystery Island",
        year=2021,
        duration_seconds=5000,
        status=MovieStatus.PUBLISHED,
    )
    # Seed active content version so title is indexed
    version = await content_repo.create_version(
        movie_id=movie.id,
        version_tag="v1.0.0",
        source_hash="spoiler-hash",
        status=ContentProcessingStatus.COMPLETED,
    )
    await content_repo.publish_version(version.id)

    headers = {"X-User-ID": "viewer-charlie"}
    create_res = await api_client.post(
        "/api/v1/sessions",
        json={"title_id": movie.id},
        headers=headers,
    )
    session_id = create_res.json()["session_id"]

    # Trigger spoiler confirmation via questions asking future events
    q_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What happens next and who dies at the end?"},
        headers=headers,
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["outcome"] == "spoiler_confirmation_required"
    nonce = q_data["confirmation_nonce"]
    assert nonce is not None

    # Consume single-use nonce to authorize FULL spoiler mode
    auth_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/spoiler-confirmation",
        json={"confirmation_nonce": nonce},
        headers=headers,
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["spoiler_mode"] == "full"
    assert auth_res.json()["status"] == "confirmed"

    # AC-010: Attempting to reuse the same nonce fails
    reuse_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/spoiler-confirmation",
        json={"confirmation_nonce": nonce},
        headers=headers,
    )
    assert reuse_res.status_code == 403
    assert "invalid or expired" in reuse_res.json()["message"].lower()

    # Revert to safe mode
    revert_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/safe-mode",
        headers=headers,
    )
    assert revert_res.status_code == 200
    assert revert_res.json()["spoiler_mode"] == "safe"

    # Delete session idempotently
    del_res = await api_client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_question_boundary_filtering_and_citations(
    api_client: AsyncClient,
    test_db_session: AsyncSession,
):
    """AC-004: Pre-retrieval boundary filtering prevents future dialogue from ever being returned."""
    movie_repo = MovieRepository(test_db_session)
    content_repo = ContentVersionRepository(test_db_session)
    chunk_repo = SubtitleChunkRepository(test_db_session)

    movie = await movie_repo.create_movie(
        title_id="time-traveler",
        display_title="The Time Traveler",
        year=2023,
        duration_seconds=7200,
        status=MovieStatus.PUBLISHED,
    )

    version = await content_repo.create_version(
        movie_id=movie.id,
        version_tag="v1.0.0",
        source_hash="srthash123",
        status=ContentProcessingStatus.COMPLETED,
    )
    await content_repo.publish_version(version.id)

    # Insert 2 chunks: one at 30-40s (past), one at 200-210s (future)
    await chunk_repo.create_chunk(
        chunk_id="chunk-early-past",
        content_version_id=version.id,
        movie_id=movie.id,
        chunk_index=0,
        start_time_seconds=30,
        end_time_seconds=40,
        text="The device is hidden inside the grandfather clock.",
    )
    await chunk_repo.create_chunk(
        chunk_id="chunk-far-future",
        content_version_id=version.id,
        movie_id=movie.id,
        chunk_index=1,
        start_time_seconds=200,
        end_time_seconds=210,
        text="The clock exploded and the villain escaped to Paris.",
    )

    headers = {"X-User-ID": "viewer-dan"}
    # Session is at position 60s (SAFE mode)
    create_res = await api_client.post(
        "/api/v1/sessions",
        json={"title_id": movie.id, "position_seconds": 60},
        headers=headers,
    )
    session_id = create_res.json()["session_id"]

    # Ask about the clock
    q_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "Where is the device hidden?"},
        headers=headers,
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["outcome"] == "answered"
    assert len(q_data["citations"]) > 0

    # AC-004 verification: Only early chunk was included in citations; future chunk was excluded
    cited_ids = [c["chunk_id"] for c in q_data["citations"]]
    assert "chunk-early-past" in cited_ids
    assert "chunk-far-future" not in cited_ids
    for c in q_data["citations"]:
        assert c["end_time_seconds"] <= 60
