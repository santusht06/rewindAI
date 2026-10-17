"""Unit and integration tests for Authorized Content Ingestion Pipeline.

Tests:
- Subtitle parsing (SRT and WebVTT)
- Timestamp and text normalization
- Deterministic chunking
- Embedding provider interface
- End-to-end IngestionPipeline
- Idempotency and duplicate avoidance (SRS-ING-002)
- Staged index isolation (SRS-ING-004)
- Admin ingestion endpoints (04_API_CONTRACT)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.api.dependencies import get_db
from services.api.domain.models import ContentProcessingStatus, MovieStatus
from services.api.errors import ValidationError
from services.api.infrastructure.repositories import (
    ContentVersionRepository,
    MovieRepository,
    SubtitleChunkRepository,
)
from services.api.infrastructure.tables import Base
from services.api.ingestion.chunker import chunk_subtitle_cues
from services.api.ingestion.embeddings import DeterministicMockEmbeddingProvider
from services.api.ingestion.parser import (
    clean_subtitle_text,
    parse_srt_or_vtt,
    parse_timestamp_to_seconds,
)
from services.api.ingestion.pipeline import IngestionPipeline
from services.api.main import create_app


SAMPLE_SRT = """1
00:00:10,500 --> 00:00:14,200
COOPER: We used to look up at the sky and wonder at our place in the stars.

2
00:00:15,000 --> 00:00:18,900
Now we just look down and worry about our place in the dirt.

3
00:00:22,100 --> 00:00:25,800
<i>MURF: Dad, look outside! The dust storm is coming.</i>
"""

SAMPLE_VTT = """WEBVTT - Interstellar Sample Cue

00:01.000 --> 00:04.500
BRAND: Love is the one thing we're capable of perceiving that transcends dimensions of time and space.

00:06.200 --> 00:09.800
Maybe we should trust that, even if we can't understand it.
"""


@pytest_asyncio.fixture
async def test_db_session():
    """In-memory SQLite async database engine for isolated ingestion testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(test_db_session: AsyncSession):
    """Async HTTP client configured with test database session."""
    app = create_app()

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ==========================================
# 1. Parser & Normalizer Tests
# ==========================================

def test_parse_timestamp_to_seconds():
    """Test SRT and VTT timestamp conversion to float seconds."""
    assert parse_timestamp_to_seconds("00:01:23,456") == 83.456
    assert parse_timestamp_to_seconds("01:00:00.000") == 3600.0
    assert parse_timestamp_to_seconds("02:15.500") == 135.5
    with pytest.raises(ValidationError):
        parse_timestamp_to_seconds("invalid-timestamp")


def test_clean_subtitle_text_and_speaker_extraction():
    """Test stripping markup and extracting speaker label."""
    cleaned, speaker = clean_subtitle_text("<b>COOPER:</b> We must go.")
    assert cleaned == "We must go."
    assert speaker == "COOPER"

    cleaned2, speaker2 = clean_subtitle_text("<i>No speaker here</i>")
    assert cleaned2 == "No speaker here"
    assert speaker2 is None


def test_parse_srt_success():
    """Verify parsing valid SRT file into structured cues."""
    cues = parse_srt_or_vtt(SAMPLE_SRT)
    assert len(cues) == 3
    assert cues[0].start_time_seconds == 10.5
    assert cues[0].end_time_seconds == 14.2
    assert cues[0].speaker == "COOPER"
    assert "look up at the sky" in cues[0].text
    assert cues[2].speaker == "MURF"
    assert "dust storm" in cues[2].text


def test_parse_vtt_success():
    """Verify parsing valid WebVTT file into structured cues."""
    cues = parse_srt_or_vtt(SAMPLE_VTT)
    assert len(cues) == 2
    assert cues[0].start_time_seconds == 1.0
    assert cues[0].end_time_seconds == 4.5
    assert cues[0].speaker == "BRAND"


def test_parse_invalid_timestamps_and_empty():
    """SRS-ING-003: Inverted timestamp ranges and empty files must raise explicit errors."""
    with pytest.raises(ValidationError, match="empty"):
        parse_srt_or_vtt("")

    inverted_srt = """1\n00:00:20,000 --> 00:00:10,000\nInverted cue.\n"""
    with pytest.raises(ValidationError, match="Inverted timestamp"):
        parse_srt_or_vtt(inverted_srt)


# ==========================================
# 2. Chunker & Embedding Tests
# ==========================================

def test_chunking_cues():
    """BE-INGEST-005: Chunking preserves time boundaries and groups sequential cues."""
    cues = parse_srt_or_vtt(SAMPLE_SRT)
    chunks = chunk_subtitle_cues(cues, max_duration_seconds=30.0)
    assert len(chunks) >= 1
    for c in chunks:
        assert c["start_time_seconds"] <= c["end_time_seconds"]
        assert c["ordinal"] >= 0
        assert len(c["text"]) > 0


@pytest.mark.asyncio
async def test_deterministic_mock_embedding_provider():
    """Verify deterministic mock embedding provider consistency."""
    provider = DeterministicMockEmbeddingProvider(dimension=128)
    assert provider.dimension == 128

    texts = [
        "The black hole gargantua in deep space",
        "The black hole gargantua in deep space",
        "A recipe for chocolate chip cookies",
    ]
    vectors = await provider.embed_texts(texts)
    assert len(vectors) == 3
    assert len(vectors[0]) == 128

    # Identical texts must produce exactly identical vectors
    assert vectors[0] == vectors[1]

    # Semantic similarity: cosine similarity of (0, 1) is 1.0
    def dot_product(v1, v2):
        return sum(a * b for a, b in zip(v1, v2))

    sim_identical = dot_product(vectors[0], vectors[1])
    sim_different = dot_product(vectors[0], vectors[2])
    assert pytest.approx(sim_identical, 0.001) == 1.0
    assert sim_different < 0.9  # Unrelated topic has significantly lower similarity


# ==========================================
# 3. End-to-End Pipeline & Idempotency
# ==========================================

@pytest.mark.asyncio
async def test_ingestion_pipeline_staged_and_idempotent(test_db_session: AsyncSession):
    """SRS-ING-002, SRS-ING-004: Ingestion is staged and idempotent without duplicate chunks."""
    movie_repo = MovieRepository(test_db_session)
    content_repo = ContentVersionRepository(test_db_session)
    chunk_repo = SubtitleChunkRepository(test_db_session)

    movie = await movie_repo.create_movie(
        title_id="interstellar-real",
        display_title="Interstellar",
        year=2014,
        duration_seconds=10140,
        status=MovieStatus.DRAFT,
    )

    pipeline = IngestionPipeline(db_session=test_db_session)

    # 1. Run first ingestion in staged mode (auto_publish=False)
    res1 = await pipeline.ingest_asset(
        movie_id=movie.id,
        raw_content=SAMPLE_SRT,
        auto_publish=False,
    )
    assert res1.cue_count == 3
    assert res1.chunk_count >= 1
    assert res1.is_active is False
    assert res1.processing_status == "completed"

    # Verify staged isolation: no active version exists yet (SRS-ING-004)
    active_ver = await content_repo.get_active_version(movie.id)
    assert active_ver is None

    chunks_count = len(
        await chunk_repo.get_chunks_within_boundary(content_version_id=res1.content_version_id)
    )
    assert chunks_count == res1.chunk_count

    # 2. Idempotency test (SRS-ING-002): Ingest identical content again
    res2 = await pipeline.ingest_asset(
        movie_id=movie.id,
        raw_content=SAMPLE_SRT,
        auto_publish=False,
    )
    assert res2.content_version_id == res1.content_version_id
    assert res2.source_checksum == res1.source_checksum

    # Verify no duplicate chunks were created
    total_chunks_after = len(
        await chunk_repo.get_chunks_within_boundary(content_version_id=res1.content_version_id)
    )
    assert total_chunks_after == chunks_count

    # 3. Publish staged version
    await content_repo.publish_version(res1.content_version_id)
    active_ver_now = await content_repo.get_active_version(movie.id)
    assert active_ver_now is not None
    assert active_ver_now.id == res1.content_version_id


# ==========================================
# 4. Admin API Endpoint Ingestion Tests
# ==========================================

@pytest.mark.asyncio
async def test_admin_ingest_and_publish_endpoints(
    api_client: AsyncClient,
    test_db_session: AsyncSession,
):
    """Test admin API endpoints for ingestion and atomic publication."""
    movie_repo = MovieRepository(test_db_session)
    movie = await movie_repo.create_movie(
        title_id="admin-film",
        display_title="Admin Science Fiction",
        year=2024,
        duration_seconds=7200,
        status=MovieStatus.DRAFT,
    )

    # 1. Unauthorized admin call is rejected
    unauth_res = await api_client.post(
        f"/api/v1/admin/titles/{movie.id}/ingest",
        json={"raw_content": SAMPLE_SRT},
        headers={"X-Admin-Token": "invalid-token"},
    )
    assert unauth_res.status_code == 403

    # 2. Ingest via admin endpoint
    ingest_res = await api_client.post(
        f"/api/v1/admin/titles/{movie.id}/ingest",
        json={"raw_content": SAMPLE_SRT, "auto_publish": False},
    )
    assert ingest_res.status_code == 201
    data = ingest_res.json()
    version_id = data["content_version_id"]
    assert data["is_active"] is False

    # 3. Publish version via admin endpoint
    pub_res = await api_client.post(
        f"/api/v1/admin/titles/{movie.id}/publish-version/{version_id}"
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    # Verify title is now published and visible on public catalog
    catalog_res = await api_client.get(f"/api/v1/titles/{movie.id}")
    assert catalog_res.status_code == 200
    assert catalog_res.json()["questions_available"] is True
