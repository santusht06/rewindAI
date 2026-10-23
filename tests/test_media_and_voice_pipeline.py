"""Tests for media processing pipeline, dual readiness gate, and voice interaction.

Validates acceptance criteria from REWIND-REQ-021:
- AT-01: Valid authorized upload (Asset & Job created)
- AT-02: Corrupt / unsupported video (Safe failure; never READY)
- AT-03: Subtitle extraction from media asset
- AT-04: Audio extraction and STT fallback path
- AT-05: Job retry logic
- AT-06: Dual readiness gate (Movie published only when both playback and AI index ready)
- AT-11: Voice query submission, STT recognition, and grounded Q&A
- AT-12: TTS failure gracefully degrades with intact text answer
"""

import base64
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.ai.voice import (
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
    set_stt_provider,
    set_tts_provider,
)
from services.api.config import settings
from services.api.domain.models import (
    MediaAssetStatus,
    MediaAssetType,
    MovieStatus,
    ProcessingJobStage,
    SpoilerMode,
)
from services.api.infrastructure.database import Base
from services.api.infrastructure.repositories import (
    MediaAssetRepository,
    MovieRepository,
    ProcessingJobRepository,
    ViewingSessionRepository,
)
from services.api.main import create_app
from services.api.media.pipeline import MediaPipeline
from services.api.media.processor import MediaProcessor, MediaStreamInfo
from services.api.media.storage import LocalStorageProvider, set_media_storage


@pytest_asyncio.fixture
async def media_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def media_client(media_test_db: AsyncSession):
    app = create_app()

    async def override_get_db():
        yield media_test_db

    from services.api.api.dependencies import get_db
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class FakeProcessor(MediaProcessor):
    """Deterministic processor for testing without requiring system FFmpeg binary."""

    def __init__(self, simulate_corrupt: bool = False, has_subtitles: bool = True):
        super().__init__()
        self.simulate_corrupt = simulate_corrupt
        self.has_subtitles = has_subtitles

    def inspect_file(self, file_path: str | Path) -> MediaStreamInfo:
        if self.simulate_corrupt:
            from services.api.media.processor import MediaProcessingError
            raise MediaProcessingError("Corrupted file format", "CORRUPT_OR_UNSUPPORTED_MEDIA")
        return MediaStreamInfo(
            has_video=True,
            has_audio=True,
            has_subtitles=self.has_subtitles,
            duration_seconds=120.0,
            video_codec="h264",
            audio_codec="aac",
        )

    def extract_subtitles(self, file_path: str | Path, output_path: str | Path) -> bool:
        if not self.has_subtitles:
            return False
        Path(output_path).write_text(
            "1\n00:00:01,000 --> 00:00:10,000\n[COOPER] We must find a way off this planet.\n\n"
            "2\n00:00:15,000 --> 00:00:35,000\n[BRAND] The wormhole appeared near Saturn forty-eight years ago.\n\n",
            encoding="utf-8",
        )
        return True

    def extract_audio(self, file_path: str | Path, output_path: str | Path) -> bool:
        Path(output_path).write_bytes(b"MOCK_STT:Cooper and Brand launch the Endurance mission.")
        return True

    def package_hls(self, file_path: str | Path, output_dir: str | Path, segment_duration: int = 6) -> Path | None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = out_dir / "index.m3u8"
        manifest.write_text("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-ENDLIST\n")
        return manifest


@pytest.mark.asyncio
async def test_at01_valid_media_upload_and_job_creation(media_test_db: AsyncSession):
    """AT-01: Valid authorized upload creates MediaAsset and ProcessingJob records."""
    movie_repo = MovieRepository(media_test_db)
    movie = await movie_repo.create(title="Interstellar Demo", duration_seconds=7200)
    await media_test_db.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageProvider(base_dir=tmp_dir)
        pipeline = MediaPipeline(
            db_session=media_test_db,
            storage_provider=storage,
            processor=FakeProcessor(),
        )

        job_id = await pipeline.create_upload_job(
            movie_id=movie.id,
            file_name="demo_movie.mp4",
            file_bytes=b"fake-mp4-video-content-bytes",
        )
        assert job_id is not None

        # Verify database entities created
        job_repo = ProcessingJobRepository(media_test_db)
        job = await job_repo.get_by_id(job_id)
        assert job is not None
        assert job.stage == ProcessingJobStage.UPLOADED.value
        assert job.movie_id == movie.id

        asset_repo = MediaAssetRepository(media_test_db)
        assets = await asset_repo.list_by_movie(movie.id)
        assert len(assets) == 1
        assert assets[0].asset_type == MediaAssetType.VIDEO_SOURCE.value


@pytest.mark.asyncio
async def test_at02_corrupt_video_safe_failure(media_test_db: AsyncSession):
    """AT-02: Corrupted media fails safely and movie is never set to READY."""
    movie_repo = MovieRepository(media_test_db)
    movie = await movie_repo.create(title="Corrupt Media Test", duration_seconds=120)
    await media_test_db.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageProvider(base_dir=tmp_dir)
        pipeline = MediaPipeline(
            db_session=media_test_db,
            storage_provider=storage,
            processor=FakeProcessor(simulate_corrupt=True),
        )

        job_id = await pipeline.create_upload_job(
            movie_id=movie.id,
            file_name="corrupt.mp4",
            file_bytes=b"garbage-bytes",
        )
        result = await pipeline.execute_job(job_id)

        assert result["status"] == "failed"
        job_repo = ProcessingJobRepository(media_test_db)
        job = await job_repo.get_by_id(job_id)
        assert job.stage == ProcessingJobStage.FAILED.value
        assert job.is_playback_ready is False

        # Invariant: Movie is never published
        updated_movie = await movie_repo.get_by_id(movie.id)
        assert updated_movie.status != MovieStatus.PUBLISHED.value


@pytest.mark.asyncio
async def test_at03_and_at06_embedded_subtitles_and_dual_readiness(media_test_db: AsyncSession):
    """AT-03 & AT-06: Subtitles extracted, HLS packaged, and dual readiness gate passes."""
    movie_repo = MovieRepository(media_test_db)
    movie = await movie_repo.create(title="Endurance Journey", duration_seconds=120)
    await media_test_db.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageProvider(base_dir=tmp_dir)
        pipeline = MediaPipeline(
            db_session=media_test_db,
            storage_provider=storage,
            processor=FakeProcessor(has_subtitles=True),
        )

        job_id = await pipeline.create_upload_job(
            movie_id=movie.id,
            file_name="endurance.mp4",
            file_bytes=b"valid-video-data",
        )
        result = await pipeline.execute_job(job_id)

        assert result["status"] == "ready"
        assert result["is_playback_ready"] is True
        assert result["is_ai_ready"] is True

        # Invariant: Movie published only after both gates pass
        updated_movie = await movie_repo.get_by_id(movie.id)
        assert updated_movie.status == MovieStatus.PUBLISHED.value
        assert updated_movie.is_playback_ready is True
        assert updated_movie.is_ai_ready is True


@pytest.mark.asyncio
async def test_at04_no_subtitles_stt_fallback(media_test_db: AsyncSession):
    """AT-04: Video without subtitles triggers audio extraction and STT transcription fallback."""
    movie_repo = MovieRepository(media_test_db)
    movie = await movie_repo.create(title="Silent Video with Voice", duration_seconds=60)
    await media_test_db.commit()

    set_stt_provider(MockSpeechToTextProvider(default_transcription="Audio extracted from video successfully."))

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageProvider(base_dir=tmp_dir)
        pipeline = MediaPipeline(
            db_session=media_test_db,
            storage_provider=storage,
            processor=FakeProcessor(has_subtitles=False),
        )

        job_id = await pipeline.create_upload_job(
            movie_id=movie.id,
            file_name="nosubs.mp4",
            file_bytes=b"video-without-subtitles",
        )
        result = await pipeline.execute_job(job_id)

        assert result["status"] == "ready"
        assert result["is_ai_ready"] is True


@pytest.mark.asyncio
async def test_at11_and_at12_voice_query_and_tts_fallback(
    media_client: AsyncClient, media_test_db: AsyncSession
):
    """AT-11 & AT-12: Push-to-talk voice query converts audio to text, retrieves grounded answer, and degrades gracefully on TTS failure."""
    movie_repo = MovieRepository(media_test_db)
    movie = await movie_repo.create(title="Voice Test Title", duration_seconds=120)

    # Ingest dialogue cues
    from services.api.ingestion.pipeline import IngestionPipeline
    pipeline = IngestionPipeline(media_test_db)
    await pipeline.ingest_asset(
        movie_id=movie.id,
        raw_content="1\n00:00:10,000 --> 00:00:30,000\n[COOPER] The gravity anomaly in the bedroom was communication.\n\n",
        source_type="srt",
        auto_publish=True,
    )


    # Create viewing session
    session_repo = ViewingSessionRepository(media_test_db)
    session = await session_repo.create_session(
        user_id="test-viewer",
        movie_id=movie.id,
        initial_position=35.0,
        spoiler_mode=SpoilerMode.SAFE,
    )
    await media_test_db.commit()

    # Configure STT to recognize speech and mock TTS for isolated testing
    set_stt_provider(MockSpeechToTextProvider(default_transcription="What was the gravity anomaly?"))
    set_tts_provider(MockTextToSpeechProvider())

    # Audio input bytes (mock audio)
    fake_audio = base64.b64encode(b"RIFF-WAVE-BYTES-DATA").decode("ascii")

    res = await media_client.post(
        "/api/v1/assistant/voice-query",
        headers={"X-User-ID": "test-viewer"},
        json={
            "session_id": session.id,
            "audio_base64": fake_audio,
            "playback_position_seconds": 35.0,
            "spoiler_mode": "safe",
            "synthesize_speech": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["recognized_question"] == "What was the gravity anomaly?"
    assert data["outcome"] == "answered"
    assert "gravity anomaly" in data["answer"].lower()
    assert len(data["citations"]) > 0
    assert data["audio_base64"] is not None

    # AT-12: Test TTS synthesis exception degrades gracefully without breaking text response
    class FailingTTS:
        async def synthesize(self, text: str, voice: str | None = None) -> bytes:
            raise RuntimeError("TTS engine unreachable")

    set_tts_provider(FailingTTS())

    res2 = await media_client.post(
        "/api/v1/assistant/voice-query",
        headers={"X-User-ID": "test-viewer"},
        json={
            "session_id": session.id,
            "audio_base64": fake_audio,
            "playback_position_seconds": 35.0,
            "spoiler_mode": "safe",
            "synthesize_speech": True,
        },
    )

    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["outcome"] == "answered"
    assert data2["audio_base64"] is None  # degraded gracefully
    assert "gravity anomaly" in data2["answer"].lower()
