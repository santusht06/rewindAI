"""Repository access layer providing typed, transactional database operations.

Implements BE-DATA-004, BE-DATA-005, SRS-CAT-001, SRS-SES-001..004, and 03_DOMAIN_MODEL_AND_DATABASE.
"""

from datetime import datetime, timezone
import json
from typing import Any
import uuid
from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.domain.models import ContentProcessingStatus, MovieStatus, ProgressSource, SpoilerMode
from services.api.errors import ConflictError, NotFoundError
from services.api.infrastructure.tables import (
    AnswerSourceTable,
    AuditEventTable,
    ContentVersionTable,
    MovieTable,
    QuestionTable,
    StoryFactTable,
    SubtitleChunkTable,
    ViewingSessionTable,
)


class MovieRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        title: str,
        release_year: int | None = None,
        language: str = "en",
        status: MovieStatus = MovieStatus.DRAFT,
        movie_id: str | None = None,
    ) -> MovieTable:
        movie = MovieTable(
            id=movie_id or str(uuid.uuid4()),
            title=title,
            release_year=release_year,
            language=language,
            status=status.value if isinstance(status, MovieStatus) else status,
        )
        self.session.add(movie)
        await self.session.flush()
        return movie

    async def get_by_id(self, movie_id: str) -> MovieTable | None:
        query = select(MovieTable).where(MovieTable.id == movie_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_published(self, limit: int = 50, offset: int = 0) -> list[MovieTable]:
        query = (
            select(MovieTable)
            .where(MovieTable.status == MovieStatus.PUBLISHED.value)
            .order_by(MovieTable.title.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(self, movie_id: str, status: MovieStatus) -> MovieTable:
        movie = await self.get_by_id(movie_id)
        if not movie:
            raise NotFoundError(f"Movie with id {movie_id} not found")
        movie.status = status.value
        await self.session.flush()
        return movie


class ContentVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_version(
        self,
        movie_id: str,
        source_type: str = "srt",
        source_checksum: str = "default_checksum",
        version_number: int | None = None,
        embedding_model: str | None = None,
    ) -> ContentVersionTable:
        if version_number is None:
            # Query highest version number for this movie
            query = select(func.coalesce(func.max(ContentVersionTable.version_number), 0)).where(
                ContentVersionTable.movie_id == movie_id
            )
            max_ver = (await self.session.execute(query)).scalar_one()
            version_number = max_ver + 1

        version = ContentVersionTable(
            id=str(uuid.uuid4()),
            movie_id=movie_id,
            source_type=source_type,
            source_checksum=source_checksum,
            version_number=version_number,
            processing_status=ContentProcessingStatus.STAGED.value,
            embedding_model=embedding_model,
            is_active=False,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_by_id(self, version_id: str) -> ContentVersionTable | None:
        query = select(ContentVersionTable).where(ContentVersionTable.id == version_id)
        return (await self.session.execute(query)).scalars().first()

    async def get_active_version(self, movie_id: str) -> ContentVersionTable | None:
        query = select(ContentVersionTable).where(
            and_(
                ContentVersionTable.movie_id == movie_id,
                ContentVersionTable.is_active.is_(True),
                ContentVersionTable.processing_status == ContentProcessingStatus.PUBLISHED.value,
            )
        )
        return (await self.session.execute(query)).scalars().first()

    async def publish_version(self, version_id: str) -> ContentVersionTable:
        """Atomically set version to active & published while deactivating any prior active version."""
        target = await self.get_by_id(version_id)
        if not target:
            raise NotFoundError(f"ContentVersion with id {version_id} not found")

        # Deactivate all versions for this movie
        await self.session.execute(
            update(ContentVersionTable)
            .where(ContentVersionTable.movie_id == target.movie_id)
            .values(is_active=False)
        )

        # Activate target version
        target.is_active = True
        target.processing_status = ContentProcessingStatus.PUBLISHED.value
        await self.session.flush()
        return target


class SubtitleChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, chunks: list[dict[str, Any]]) -> int:
        """Insert a batch of subtitle chunks."""
        if not chunks:
            return 0
        instances = [
            SubtitleChunkTable(
                id=c.get("id") or str(uuid.uuid4()),
                content_version_id=c["content_version_id"],
                movie_id=c["movie_id"],
                ordinal=c["ordinal"],
                start_time_seconds=c["start_time_seconds"],
                end_time_seconds=c["end_time_seconds"],
                start_time_formatted=c["start_time_formatted"],
                end_time_formatted=c["end_time_formatted"],
                text=c["text"],
                speaker=c.get("speaker"),
                embedding_json=json.dumps(c["embedding"]) if c.get("embedding") else None,
            )
            for c in chunks
        ]
        self.session.add_all(instances)
        await self.session.flush()
        return len(instances)

    async def get_chunks_within_boundary(
        self,
        content_version_id: str,
        max_end_time_seconds: float | None = None,
        limit: int = 100,
    ) -> list[SubtitleChunkTable]:
        """Query chunks strictly at or before max_end_time_seconds (for spoiler safety)."""
        conditions = [SubtitleChunkTable.content_version_id == content_version_id]
        if max_end_time_seconds is not None:
            conditions.append(SubtitleChunkTable.end_time_seconds <= max_end_time_seconds)

        query = (
            select(SubtitleChunkTable)
            .where(and_(*conditions))
            .order_by(SubtitleChunkTable.ordinal.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ViewingSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        movie_id: str,
        user_id: str = "anonymous",
        current_position_seconds: float = 0.0,
        progress_source: ProgressSource = ProgressSource.UNKNOWN,
        spoiler_mode: SpoilerMode = SpoilerMode.SAFE,
        session_id: str | None = None,
    ) -> ViewingSessionTable:
        session_obj = ViewingSessionTable(
            id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            movie_id=movie_id,
            current_position_seconds=max(0.0, current_position_seconds),
            progress_source=progress_source.value,
            spoiler_mode=spoiler_mode.value,
            full_spoilers_confirmed=False,
        )
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_by_id(self, session_id: str) -> ViewingSessionTable | None:
        query = select(ViewingSessionTable).where(ViewingSessionTable.id == session_id)
        return (await self.session.execute(query)).scalars().first()

    async def update_progress(
        self,
        session_id: str,
        position_seconds: float,
        source: ProgressSource = ProgressSource.MANUAL,
    ) -> ViewingSessionTable:
        sess = await self.get_by_id(session_id)
        if not sess:
            raise NotFoundError(f"Session with id {session_id} not found")
        sess.current_position_seconds = max(0.0, position_seconds)
        sess.progress_source = source.value
        await self.session.flush()
        return sess

    async def issue_spoiler_nonce(
        self, session_id: str, nonce: str, expires_at: datetime
    ) -> ViewingSessionTable:
        sess = await self.get_by_id(session_id)
        if not sess:
            raise NotFoundError(f"Session with id {session_id} not found")
        sess.spoiler_confirmation_nonce = nonce
        sess.spoiler_nonce_expires_at = expires_at
        await self.session.flush()
        return sess

    async def confirm_spoiler_mode(self, session_id: str, nonce: str) -> ViewingSessionTable:
        sess = await self.get_by_id(session_id)
        if not sess:
            raise NotFoundError(f"Session with id {session_id} not found")

        # Validate nonce
        if not sess.spoiler_confirmation_nonce or sess.spoiler_confirmation_nonce != nonce:
            raise ConflictError("Invalid or expired spoiler confirmation token")

        now = datetime.now(timezone.utc)
        if sess.spoiler_nonce_expires_at and sess.spoiler_nonce_expires_at < now:
            raise ConflictError("Spoiler confirmation token has expired")

        sess.spoiler_mode = SpoilerMode.FULL.value
        sess.full_spoilers_confirmed = True
        sess.spoiler_confirmation_nonce = None
        sess.spoiler_nonce_expires_at = None
        await self.session.flush()
        return sess

    async def reset_to_safe_mode(self, session_id: str) -> ViewingSessionTable:
        sess = await self.get_by_id(session_id)
        if not sess:
            raise NotFoundError(f"Session with id {session_id} not found")
        sess.spoiler_mode = SpoilerMode.SAFE.value
        sess.full_spoilers_confirmed = False
        sess.spoiler_confirmation_nonce = None
        await self.session.flush()
        return sess


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_question(
        self,
        session_id: str,
        movie_id: str,
        question_text: str,
        request_id: str,
        playback_position_seconds: float,
        spoiler_mode: str,
        status: str = "answered",
        answer_text: str | None = None,
    ) -> QuestionTable:
        q = QuestionTable(
            id=str(uuid.uuid4()),
            session_id=session_id,
            movie_id=movie_id,
            question_text=question_text,
            request_id=request_id,
            playback_position_seconds=playback_position_seconds,
            spoiler_mode=spoiler_mode,
            status=status,
            answer_text=answer_text,
        )
        self.session.add(q)
        await self.session.flush()
        return q

    async def add_citations(
        self, question_id: str, citations: list[dict[str, Any]]
    ) -> None:
        sources = [
            AnswerSourceTable(
                id=str(uuid.uuid4()),
                question_id=question_id,
                chunk_id=c.get("chunk_id"),
                story_fact_id=c.get("story_fact_id"),
                relevance_score=c.get("relevance_score"),
            )
            for c in citations
        ]
        self.session.add_all(sources)
        await self.session.flush()


class AuditEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_event(
        self,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEventTable:
        event = AuditEventTable(
            id=str(uuid.uuid4()),
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            correlation_id=correlation_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.session.add(event)
        await self.session.flush()
        return event
