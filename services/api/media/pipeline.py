"""End-to-end media ingestion and processing pipeline.

Adheres to:
- REWIND-REQ-018 (FR-03: Media processing, FR-04: Subtitle ingestion, FR-05: Chunking & Indexing)
- REWIND-REQ-019 (Section 2: Job stages, Section 3: FFprobe/FFmpeg, Dual readiness gate)
- AT-01, AT-02, AT-03, AT-04, AT-05, AT-06
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.ai.voice import get_stt_provider
from services.api.domain.models import (
    MediaAssetStatus,
    MediaAssetType,
    MovieStatus,
    ProcessingJobStage,
)
from services.api.errors import NotFoundError, ValidationError
from services.api.infrastructure.repositories import (
    MediaAssetRepository,
    MovieRepository,
    ProcessingJobRepository,
)
from services.api.ingestion.embeddings import EmbeddingProvider
from services.api.ingestion.pipeline import IngestionPipeline
from services.api.media.processor import MediaProcessor, MediaProcessingError
from services.api.media.storage import MediaStorageProvider, get_media_storage


class MediaPipeline:
    """Orchestrates asynchronous media processing and dual readiness gates."""

    def __init__(
        self,
        db_session: AsyncSession,
        storage_provider: MediaStorageProvider | None = None,
        processor: MediaProcessor | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = db_session
        self.storage = storage_provider or get_media_storage()
        self.processor = processor or MediaProcessor()
        self.movie_repo = MovieRepository(db_session)
        self.asset_repo = MediaAssetRepository(db_session)
        self.job_repo = ProcessingJobRepository(db_session)
        self.ingestion_pipeline = IngestionPipeline(db_session, embedding_provider)

    async def create_upload_job(
        self,
        movie_id: str,
        file_name: str,
        file_bytes: bytes,
        content_type: str = "video/mp4",
        supplied_srt_content: str | None = None,
    ) -> str:
        """Store uploaded video file and initiate processing job."""
        movie = await self.movie_repo.get_by_id(movie_id)
        if not movie:
            raise NotFoundError(f"Movie {movie_id} not found")

        # 1. Store source binary
        storage_path, stream_url = await self.storage.store(file_name, file_bytes, content_type)
        asset = await self.asset_repo.create(
            movie_id=movie_id,
            asset_type=MediaAssetType.VIDEO_SOURCE,
            storage_path=storage_path,
            stream_url=stream_url,
            file_size_bytes=len(file_bytes),
            status=MediaAssetStatus.READY,
        )

        # 2. Create durable processing job
        job = await self.job_repo.create(
            movie_id=movie_id,
            stage=ProcessingJobStage.UPLOADED,
        )
        return job.id

    async def execute_job(
        self,
        job_id: str,
        supplied_srt_content: str | None = None,
    ) -> dict[str, str | bool | None]:
        """Execute all media inspection, packaging, subtitle extraction, and AI indexing stages."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"ProcessingJob {job_id} not found")

        movie = await self.movie_repo.get_by_id(job.movie_id)
        if not movie:
            raise NotFoundError(f"Movie {job.movie_id} not found")

        assets = await self.asset_repo.list_by_movie(job.movie_id)
        source_asset = next(
            (a for a in assets if a.asset_type == MediaAssetType.VIDEO_SOURCE.value), None
        )
        if not source_asset:
            await self.job_repo.mark_failed(job_id, "MISSING_SOURCE_ASSET", "Source video asset not found", False)
            return {"status": "failed", "error": "Missing source asset"}

        try:
            # Stage 1: INSPECTING
            await self.job_repo.update_stage(job_id, ProcessingJobStage.INSPECTING)
            stream_info = self.processor.inspect_file(source_asset.storage_path)

            # Update asset with real duration and codec
            await self.asset_repo.update_status(
                source_asset.id,
                MediaAssetStatus.READY,
                duration_seconds=stream_info.duration_seconds,
                codec=stream_info.video_codec,
            )

            # Stage 2: MEDIA_PROCESSING (Packaging and stream verification)
            await self.job_repo.update_stage(job_id, ProcessingJobStage.MEDIA_PROCESSING)
            stream_url = source_asset.stream_url
            is_playback_ready = False

            # Try HLS packaging
            with tempfile.TemporaryDirectory() as tmp_dir:
                hls_manifest = self.processor.package_hls(source_asset.storage_path, tmp_dir)
                if hls_manifest and hls_manifest.exists():
                    # Read manifest and store in media storage
                    manifest_bytes = hls_manifest.read_bytes()
                    hls_path, hls_url = await self.storage.store(
                        f"{job.movie_id}_stream.m3u8", manifest_bytes, "application/x-mpegURL"
                    )
                    await self.asset_repo.create(
                        movie_id=job.movie_id,
                        asset_type=MediaAssetType.HLS_STREAM,
                        storage_path=hls_path,
                        stream_url=hls_url,
                        duration_seconds=stream_info.duration_seconds,
                        status=MediaAssetStatus.READY,
                    )
                    stream_url = hls_url
                    is_playback_ready = True
                else:
                    # Direct MP4 playback fallback
                    is_playback_ready = stream_info.has_video

            # Update movie playback metadata
            movie.stream_url = stream_url
            if stream_info.duration_seconds > 0:
                movie.duration_seconds = int(stream_info.duration_seconds)
            movie.is_playback_ready = is_playback_ready
            await self.job_repo.update_stage(job_id, ProcessingJobStage.MEDIA_PROCESSING, is_playback_ready=is_playback_ready)

            # Stage 3: TRANSCRIPT_EXTRACTING
            await self.job_repo.update_stage(job_id, ProcessingJobStage.TRANSCRIPT_EXTRACTING)
            raw_srt = supplied_srt_content

            if not raw_srt and stream_info.has_subtitles:
                with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp_srt:
                    tmp_srt_path = Path(tmp_srt.name)
                try:
                    extracted = self.processor.extract_subtitles(source_asset.storage_path, tmp_srt_path)
                    if extracted and tmp_srt_path.stat().st_size > 0:
                        raw_srt = tmp_srt_path.read_text(encoding="utf-8", errors="replace")
                finally:
                    if tmp_srt_path.exists():
                        tmp_srt_path.unlink()

            if not raw_srt:
                # STT fallback path (AT-04)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    tmp_wav_path = Path(tmp_wav.name)
                try:
                    audio_extracted = self.processor.extract_audio(source_asset.storage_path, tmp_wav_path)
                    if audio_extracted and tmp_wav_path.stat().st_size > 0:
                        stt = get_stt_provider()
                        wav_bytes = tmp_wav_path.read_bytes()
                        transcribed_text = await stt.transcribe(wav_bytes)
                        if transcribed_text:
                            # Generate a baseline synthetic SRT timestamp
                            raw_srt = (
                                f"1\n00:00:05,000 --> 00:00:30,000\n{transcribed_text}\n\n"
                            )
                finally:
                    if tmp_wav_path.exists():
                        tmp_wav_path.unlink()

            # Stage 4: TRANSCRIPT_NORMALIZING, CHUNKING, EMBEDDING, INDEXING
            is_ai_ready = False
            if raw_srt:
                await self.job_repo.update_stage(job_id, ProcessingJobStage.TRANSCRIPT_NORMALIZING)
                await self.job_repo.update_stage(job_id, ProcessingJobStage.CHUNKING)
                await self.job_repo.update_stage(job_id, ProcessingJobStage.EMBEDDING)
                await self.job_repo.update_stage(job_id, ProcessingJobStage.INDEXING)

                ingest_res = await self.ingestion_pipeline.ingest_asset(
                    movie_id=job.movie_id,
                    raw_content=raw_srt,
                    source_type="srt",
                    auto_publish=True,
                )
                is_ai_ready = ingest_res.chunk_count > 0


            movie.is_ai_ready = is_ai_ready

            # Stage 5: DUAL READINESS GATE (REWIND-REQ-019 Section 2)
            if is_playback_ready and is_ai_ready:
                movie.status = MovieStatus.PUBLISHED.value
                await self.job_repo.update_stage(
                    job_id, ProcessingJobStage.READY, is_playback_ready=True, is_ai_ready=True
                )
                await self.session.commit()
                return {
                    "status": "ready",
                    "movie_id": movie.id,
                    "is_playback_ready": True,
                    "is_ai_ready": True,
                    "stream_url": movie.stream_url,
                }
            else:
                # Fails closed if dual readiness gate cannot be established
                await self.job_repo.update_stage(
                    job_id,
                    ProcessingJobStage.FAILED,
                    is_playback_ready=is_playback_ready,
                    is_ai_ready=is_ai_ready,
                )
                await self.session.commit()
                return {
                    "status": "failed",
                    "movie_id": movie.id,
                    "is_playback_ready": is_playback_ready,
                    "is_ai_ready": is_ai_ready,
                    "error": "Failed dual readiness gate: both playback and AI index must be ready",
                }

        except MediaProcessingError as exc:
            await self.job_repo.mark_failed(job_id, exc.error_code, str(exc), False)
            await self.session.commit()
            return {"status": "failed", "error_code": exc.error_code, "error": str(exc)}
        except Exception as exc:
            await self.job_repo.mark_failed(job_id, "UNEXPECTED_ERROR", str(exc), True)
            await self.session.commit()
            return {"status": "failed", "error_code": "UNEXPECTED_ERROR", "error": str(exc)}
