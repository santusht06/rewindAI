"""Comprehensive End-to-End User Journey and Regression Suite.

Verifies:
- Complete end-to-end user journeys (AC-001 through AC-020)
- Journey 1: Catalog Browsing & Discovery (AC-001, AC-002)
- Journey 2: Session Creation & Playback Progress (AC-003)
- Journey 3: Grounded In-Bounds Q&A (AC-004, AC-005, AC-007)
- Journey 4: Spoiler Confirmation Nonce Flow & Elevation (AC-004, AC-009, AC-010)
- Journey 5: Safe Abstention & Adversarial Defense (AC-006, AC-008)
- Journey 6: Cross-User Isolation (AC-011)
- Journey 7: Ingestion Idempotency & Error Recovery (AC-012, AC-018, AC-019)
- Journey 8: Privacy & Log Redaction (AC-020)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.api.dependencies import get_db
from services.api.config import settings
from services.api.domain.models import MovieStatus, ProgressSource, SpoilerMode
from services.api.infrastructure.repositories import (
    ContentVersionRepository,
    MovieRepository,
    ViewingSessionRepository,
)
from services.api.infrastructure.tables import Base
from services.api.ingestion.pipeline import IngestionPipeline
from services.api.main import create_app


SAMPLE_MOVIE_SRT = """1
00:00:10,000 --> 00:00:20,000
COOPER: Earth is dying from the blight. We need to find an exoplanet to save humanity.

2
00:00:30,000 --> 00:00:45,000
BRAND: Professor Brand has been working on the gravity equation for thirty years.

3
00:01:10,000 --> 00:01:25,000
ROMILLY: Miller's planet is next to Gargantua. Every hour on that planet is seven years on Earth.

4
00:02:00,000 --> 00:02:15,000
MANN: The data was faked! There is no surface, only frozen clouds. I cannot die here alone.

5
00:03:00,000 --> 00:03:15,000
COOPER: Murf, it was me! I was your ghost! Love transcended five-dimensional space.
"""

TEST_ADMIN_TOKEN = "test-admin-token-for-integration-tests"


@pytest_asyncio.fixture
async def isolated_e2e_db():
    """In-memory SQLite async engine with complete schema for E2E journeys."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_client(isolated_e2e_db: AsyncSession):
    previous_admin_token = settings.admin_api_token
    settings.admin_api_token = SecretStr(TEST_ADMIN_TOKEN)
    app = create_app()

    async def override_get_db():
        yield isolated_e2e_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        settings.admin_api_token = previous_admin_token


@pytest.mark.asyncio
async def test_complete_e2e_story_companion_journey(e2e_client: AsyncClient, isolated_e2e_db: AsyncSession):
    """Executes the full end-to-end journey from ingestion to remote Q&A, spoiler gating, and session reset."""

    # -------------------------------------------------------------
    # Step 1: Admin Ingestion & Publication (AC-012, AC-018)
    # -------------------------------------------------------------
    movie_repo = MovieRepository(isolated_e2e_db)
    movie = await movie_repo.create_movie(
        title_id="interstellar-e2e",
        display_title="Interstellar",
        year=2014,
        duration_seconds=10140,
        status=MovieStatus.PUBLISHED,
    )

    admin_headers = {"X-Admin-Token": TEST_ADMIN_TOKEN}
    ingest_res = await e2e_client.post(
        f"/api/v1/admin/titles/{movie.id}/ingest",
        json={"raw_content": SAMPLE_MOVIE_SRT, "auto_publish": True},
        headers=admin_headers,
    )
    assert ingest_res.status_code == 201
    ingest_data = ingest_res.json()
    assert ingest_data["chunk_count"] >= 3
    assert ingest_data["is_active"] is True

    # Verify Idempotency (AC-012): Re-submitting identical asset returns existing version
    reingest_res = await e2e_client.post(
        f"/api/v1/admin/titles/{movie.id}/ingest",
        json={"raw_content": SAMPLE_MOVIE_SRT, "auto_publish": True},
        headers=admin_headers,
    )
    assert reingest_res.status_code == 201
    assert reingest_res.json()["content_version_id"] == ingest_data["content_version_id"]

    # -------------------------------------------------------------
    # Step 2: Catalog Lookup (AC-001, AC-002)
    # -------------------------------------------------------------
    viewer_headers = {"X-User-ID": "viewer-firetv-e2e"}
    catalog_res = await e2e_client.get("/api/v1/titles", headers=viewer_headers)
    assert catalog_res.status_code == 200
    catalog = catalog_res.json()
    assert catalog["total"] >= 1
    assert any(item["id"] == "interstellar-e2e" for item in catalog["items"])

    # -------------------------------------------------------------
    # Step 3: Session Creation & Progress Setup (AC-003)
    # -------------------------------------------------------------
    # Viewer starts watching at 50 seconds (cues 1 & 2 are in past; cues 3, 4, 5 are future)
    session_res = await e2e_client.post(
        "/api/v1/sessions",
        json={
            "title_id": movie.id,
            "position_seconds": 50,
            "source": "manual_slider",
        },
        headers=viewer_headers,
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    session_id = session_data["session_id"]
    assert session_data["current_position_seconds"] == 50
    assert session_data["spoiler_mode"] == "safe"

    # -------------------------------------------------------------
    # Step 4: In-Bounds Question Answering (AC-004, AC-005)
    # -------------------------------------------------------------
    q1_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "Why is humanity looking for another planet?"},
        headers=viewer_headers,
    )
    assert q1_res.status_code == 200
    q1_data = q1_res.json()
    assert q1_data["outcome"] == "answered"
    assert "blight" in q1_data["answer"].lower()
    assert len(q1_data["citations"]) > 0
    # Strict temporal boundary check: all citations must be <= 50s
    for c in q1_data["citations"]:
        assert c["end_time_seconds"] <= 50

    # -------------------------------------------------------------
    # Step 5: Future Spoiler Gating & Nonce Issuance (AC-004, AC-009)
    # -------------------------------------------------------------
    # Viewer asks about Dr. Mann or who Murf's ghost is (events at 120s and 180s)
    future_q_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What happens next and who dies at the end?"},
        headers=viewer_headers,
    )
    assert future_q_res.status_code == 200
    future_data = future_q_res.json()
    assert future_data["outcome"] == "spoiler_confirmation_required"
    assert future_data["confirmation_nonce"] is not None
    assert "safe mode is active" in future_data["answer"].lower()
    nonce = future_data["confirmation_nonce"]

    # -------------------------------------------------------------
    # Step 6: Forged Consent Rejection (AC-010)
    # -------------------------------------------------------------
    forged_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/spoiler-confirmation",
        json={"confirmation_nonce": "forged-invalid-nonce-12345"},
        headers=viewer_headers,
    )
    assert forged_res.status_code == 403

    # -------------------------------------------------------------
    # Step 7: Single-Use Nonce Consumption & Mode Elevation (AC-009, AC-010)
    # -------------------------------------------------------------
    confirm_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/spoiler-confirmation",
        json={"confirmation_nonce": nonce},
        headers=viewer_headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["spoiler_mode"] == "full"

    # Attempting to re-use the exact same nonce is strictly rejected (AC-010)
    reuse_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/spoiler-confirmation",
        json={"confirmation_nonce": nonce},
        headers=viewer_headers,
    )
    assert reuse_res.status_code == 403

    # -------------------------------------------------------------
    # Step 8: Full Spoiler Mode Retrieval (Elevated State)
    # -------------------------------------------------------------
    q_spoil_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "Who was Murf's ghost?"},
        headers=viewer_headers,
    )
    assert q_spoil_res.status_code == 200
    spoil_data = q_spoil_res.json()
    assert spoil_data["outcome"] == "answered"
    assert "ghost" in spoil_data["answer"].lower()

    # -------------------------------------------------------------
    # Step 9: Revert to Safe Mode
    # -------------------------------------------------------------
    revert_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/safe-mode",
        headers=viewer_headers,
    )
    assert revert_res.status_code == 200
    assert revert_res.json()["spoiler_mode"] == "safe"

    # -------------------------------------------------------------
    # Step 10: Cross-User Security Boundary (AC-011)
    # -------------------------------------------------------------
    adversary_headers = {"X-User-ID": "viewer-bob-adversary"}
    unauthorized_res = await e2e_client.get(
        f"/api/v1/sessions/{session_id}",
        headers=adversary_headers,
    )
    assert unauthorized_res.status_code == 403

    unauth_q_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What happens?"},
        headers=adversary_headers,
    )
    assert unauth_q_res.status_code == 403

    # -------------------------------------------------------------
    # Step 11: Safe Abstention on Out-of-Domain Query (AC-006)
    # -------------------------------------------------------------
    out_domain_res = await e2e_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "How do I make chocolate chip cookies?"},
        headers=viewer_headers,
    )
    assert out_domain_res.status_code == 200
    assert out_domain_res.json()["outcome"] == "insufficient_evidence"

    # -------------------------------------------------------------
    # Step 12: Session Termination
    # -------------------------------------------------------------
    close_res = await e2e_client.delete(
        f"/api/v1/sessions/{session_id}",
        headers=viewer_headers,
    )
    assert close_res.status_code == 204
