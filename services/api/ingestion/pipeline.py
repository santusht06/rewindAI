"""Ingestion pipeline orchestrating parsing, validation, chunking, embedding, and staged indexing.

Adheres strictly to:
- SRS-ING-001 through SRS-ING-007
- NFR-REL-003, NFR-SEC-002, NFR-OBS-001
- 04_content_ingestion_pipeline.mmd
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.domain.models import (
    AuditAction,
    ContentProcessingStatus,
    MovieStatus,
)
from services.api.errors import ConflictError, NotFoundError, ValidationError
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    SubtitleChunkRepository,
    SubtitleCueRepository,
)
from services.api.infrastructure.tables import ContentVersionTable
from services.api.ingestion.chunker import chunk_subtitle_cues
from services.api.ingestion.embeddings import EmbeddingProvider, get_embedding_provider
from services.api.ingestion.parser import parse_srt_or_vtt


@dataclass
class IngestionResult:
    """Detailed summary of completed ingestion execution."""
    movie_id: str
    content_version_id: str
    version_number: int
    source_checksum: str
    cue_count: int
    chunk_count: int
    duration_seconds: float
    is_active: bool
    processing_status: str
    elapsed_milliseconds: float


class IngestionPipeline:
    """Transactional, idempotent ingestion processor for authorized subtitle assets."""

    def __init__(
        self,
        db_session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = db_session
        self.movie_repo = MovieRepository(db_session)
        self.content_repo = ContentVersionRepository(db_session)
        self.chunk_repo = SubtitleChunkRepository(db_session)
        self.audit_repo = AuditEventRepository(db_session)
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def ingest_asset(
        self,
        movie_id: str,
        raw_content: str,
        source_type: str = "srt",
        auto_publish: bool = False,
        actor: str = "system_ingest",
    ) -> IngestionResult:
        """Process, validate, chunk, embed, and stage an authorized subtitle asset."""
        start_time = time.monotonic()

        # 1. Verify movie exists
        movie = await self.movie_repo.get_by_id(movie_id)
        if not movie:
            raise NotFoundError(f"Target movie '{movie_id}' not found.")

        # 2. Check asset validity and compute SHA256 checksum
        if not raw_content or not raw_content.strip():
            raise ValidationError("Ingestion asset content cannot be empty.")

        source_bytes = raw_content.encode("utf-8")
        checksum = hashlib.sha256(source_bytes).hexdigest()

        # 3. Idempotency Check (SRS-ING-002)
        # Check if identical checksum already published for this movie
        query = select(ContentVersionTable).where(
            ContentVersionTable.movie_id == movie_id,
            ContentVersionTable.source_checksum == checksum,
        )
        existing_version = (await self.session.execute(query)).scalars().first()
        if existing_version:
            # If already published or completed, return idempotent result
            elapsed = (time.monotonic() - start_time) * 1000.0
            return IngestionResult(
                movie_id=movie_id,
                content_version_id=existing_version.id,
                version_number=existing_version.version_number,
                source_checksum=checksum,
                cue_count=0,
                chunk_count=0,
                duration_seconds=movie.duration_seconds,
                is_active=existing_version.is_active,
                processing_status=existing_version.processing_status,
                elapsed_milliseconds=round(elapsed, 2),
            )

        # 4. Parse subtitle cues (handles malformed timestamps, tags, encoding)
        cues = parse_srt_or_vtt(raw_content)

        # 5. Deterministic chunking (BE-INGEST-005)
        chunk_dicts = chunk_subtitle_cues(cues)

        # 6. Stage Content Version (SRS-ING-004: incomplete indexing is NOT visible as published)
        version = await self.content_repo.create_version(
            movie_id=movie_id,
            source_type=source_type,
            source_checksum=checksum,
            embedding_model=self.embedding_provider.model_name,
            status=ContentProcessingStatus.PROCESSING,
        )

        # 7. Generate embeddings in batch
        texts_to_embed = [c["text"] for c in chunk_dicts]
        embeddings = await self.embedding_provider.embed_texts(texts_to_embed)

        # 8. Persist chunks with embeddings and foreign key to version
        for i, c_dict in enumerate(chunk_dicts):
            c_dict["content_version_id"] = version.id
            c_dict["movie_id"] = movie_id
            c_dict["embedding"] = embeddings[i] if i < len(embeddings) else None

        await self.chunk_repo.bulk_create(chunk_dicts)
        await SubtitleCueRepository(self.session).bulk_create(
            content_version_id=version.id,
            movie_id=movie_id,
            cues=cues,
        )

        # 9. Mark version completed
        version.processing_status = ContentProcessingStatus.COMPLETED.value
        await self.session.flush()

        # 10. Auto-publish if requested (SRS-ING-004, SRS-ING-005)
        if auto_publish:
            await self.content_repo.publish_version(version.id)
            if movie.status != MovieStatus.PUBLISHED.value:
                movie.status = MovieStatus.PUBLISHED.value
                await self.session.flush()

        # 11. Audit Event (SRS-ING-007, SRS-ADM-002)
        await self.audit_repo.record_event(
            action=AuditAction.PUBLISH if auto_publish else AuditAction.REINDEX,
            target_type="content_version",
            target_id=version.id,
            actor=actor,
            details={
                "movie_id": movie_id,
                "source_checksum": checksum,
                "cue_count": len(cues),
                "chunk_count": len(chunk_dicts),
                "auto_published": auto_publish,
            },
        )

        elapsed = (time.monotonic() - start_time) * 1000.0
        return IngestionResult(
            movie_id=movie_id,
            content_version_id=version.id,
            version_number=version.version_number,
            source_checksum=checksum,
            cue_count=len(cues),
            chunk_count=len(chunk_dicts),
            duration_seconds=chunk_dicts[-1]["end_time_seconds"] if chunk_dicts else 0.0,
            is_active=version.is_active,
            processing_status=version.processing_status,
            elapsed_milliseconds=round(elapsed, 2),
        )
