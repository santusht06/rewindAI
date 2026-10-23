"""Repository access layer providing typed, transactional database operations.

Implements BE-DATA-004, BE-DATA-005, SRS-CAT-001, SRS-SES-001..004, and 03_DOMAIN_MODEL_AND_DATABASE.
"""

import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.domain.models import (
    AuditAction,
    ContentProcessingStatus,
    MediaAssetStatus,
    MediaAssetType,
    MovieStatus,
    ProcessingJobStage,
    ProgressSource,
    QuestionStatus,
    SpoilerMode,
)
from services.api.errors import ConflictError, NotFoundError
from services.api.infrastructure.tables import (
    AnswerSourceTable,
    AuditEventTable,
    ContentVersionTable,
    MediaAssetTable,
    MovieTable,
    ProcessingJobTable,
    QuestionTable,
    StoryFactTable,
    SubtitleChunkTable,
    SubtitleCueTable,
    ViewingSessionTable,
)
from services.api.ingestion.parser import SubtitleCue



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
        duration_seconds: int = 7200,
    ) -> MovieTable:
        movie = MovieTable(
            id=movie_id or str(uuid.uuid4()),
            title=title,
            release_year=release_year,
            duration_seconds=duration_seconds,
            language=language,
            status=status.value if isinstance(status, MovieStatus) else status,
        )
        self.session.add(movie)
        await self.session.flush()
        return movie

    async def create_movie(
        self,
        title_id: str | None = None,
        display_title: str | None = None,
        title: str | None = None,
        year: int | None = None,
        release_year: int | None = None,
        duration_seconds: int = 7200,
        status: MovieStatus = MovieStatus.DRAFT,
        language: str = "en",
    ) -> MovieTable:
        actual_title = display_title or title or "Untitled"
        actual_year = year if year is not None else release_year
        return await self.create(
            title=actual_title,
            release_year=actual_year,
            duration_seconds=duration_seconds,
            language=language,
            status=status,
            movie_id=title_id,
        )

    async def get_by_id(self, movie_id: str) -> MovieTable | None:
        query = select(MovieTable).where(MovieTable.id == movie_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_published(
        self,
        limit: int = 50,
        offset: int = 0,
        query: str | None = None,
    ) -> list[MovieTable]:
        stmt = select(MovieTable).where(MovieTable.status == MovieStatus.PUBLISHED.value)
        if query and query.strip():
            stmt = stmt.where(MovieTable.title.ilike(f"%{query.strip()}%"))
        stmt = stmt.order_by(MovieTable.title.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
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
        source_checksum: str | None = None,
        source_hash: str | None = None,
        version_number: int | None = None,
        version_tag: str | None = None,
        embedding_model: str | None = None,
        status: ContentProcessingStatus | str | None = None,
    ) -> ContentVersionTable:
        actual_checksum = source_hash or source_checksum or "default_checksum"
        if version_number is None and version_tag:
            # Extract number from v1.0.0 or similar if possible
            digits = "".join(filter(str.isdigit, version_tag))
            version_number = int(digits) if digits else None

        if version_number is None:
            # Query highest version number for this movie
            query = select(func.coalesce(func.max(ContentVersionTable.version_number), 0)).where(
                ContentVersionTable.movie_id == movie_id
            )
            max_ver = (await self.session.execute(query)).scalar_one()
            version_number = max_ver + 1

        actual_status = ContentProcessingStatus.STAGED.value
        if status:
            actual_status = status.value if isinstance(status, ContentProcessingStatus) else status

        version = ContentVersionTable(
            id=str(uuid.uuid4()),
            movie_id=movie_id,
            source_type=source_type,
            source_checksum=actual_checksum,
            version_number=version_number,
            processing_status=actual_status,
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

    async def deactivate_all_versions(self, movie_id: str) -> None:
        """Atomically deactivate all versions for a movie (unpublishing / rights revocation)."""
        await self.session.execute(
            update(ContentVersionTable)
            .where(ContentVersionTable.movie_id == movie_id)
            .values(is_active=False)
        )
        await self.session.flush()


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

    async def create_chunk(
        self,
        content_version_id: str,
        movie_id: str,
        start_time_seconds: float,
        end_time_seconds: float,
        text: str,
        chunk_id: str | None = None,
        chunk_index: int | None = None,
        ordinal: int | None = None,
        speaker: str | None = None,
        embedding: list[float] | None = None,
    ) -> SubtitleChunkTable:
        chunk = SubtitleChunkTable(
            id=chunk_id or str(uuid.uuid4()),
            content_version_id=content_version_id,
            movie_id=movie_id,
            ordinal=ordinal if ordinal is not None else (chunk_index if chunk_index is not None else 0),
            start_time_seconds=start_time_seconds,
            end_time_seconds=end_time_seconds,
            start_time_formatted=f"{int(start_time_seconds)}s",
            end_time_formatted=f"{int(end_time_seconds)}s",
            text=text,
            speaker=speaker,
            embedding_json=json.dumps(embedding) if embedding else None,
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def get_chunks_within_boundary(
        self,
        content_version_id: str,
        max_end_time_seconds: float | None = None,
        movie_id: str | None = None,
        limit: int = 100,
    ) -> list[SubtitleChunkTable]:
        """Query chunks strictly at or before max_end_time_seconds (for spoiler safety)."""
        conditions = [SubtitleChunkTable.content_version_id == content_version_id]
        if movie_id:
            conditions.append(SubtitleChunkTable.movie_id == movie_id)
        if max_end_time_seconds is not None:
            conditions.append(SubtitleChunkTable.start_time_seconds <= max_end_time_seconds)

        query = (
            select(SubtitleChunkTable)
            .where(and_(*conditions))
            .order_by(SubtitleChunkTable.ordinal.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

class SubtitleCueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(
        self,
        content_version_id: str,
        movie_id: str,
        cues: list[SubtitleCue],
    ) -> int:
        entries = [
            SubtitleCueTable(
                id=str(uuid.uuid4()),
                content_version_id=content_version_id,
                movie_id=movie_id,
                ordinal=ordinal,
                start_time_seconds=cue.start_time_seconds,
                end_time_seconds=cue.end_time_seconds,
                text=cue.text,
                speaker=cue.speaker,
            )
            for ordinal, cue in enumerate(cues)
        ]
        self.session.add_all(entries)
        await self.session.flush()
        return len(entries)

    async def search_within_boundary(
        self,
        content_version_id: str,
        query_text: str,
        max_end_time_seconds: float,
        limit: int = 20,
    ) -> list[SubtitleCueTable]:
        escaped_query = query_text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = (
            select(SubtitleCueTable)
            .where(
                and_(
                    SubtitleCueTable.content_version_id == content_version_id,
                    SubtitleCueTable.end_time_seconds <= max_end_time_seconds,
                    SubtitleCueTable.text.ilike(f"%{escaped_query}%", escape="\\"),
                )
            )
            .order_by(SubtitleCueTable.ordinal.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_cue(
        self,
        cue_id: str,
        content_version_id: str,
        max_end_time_seconds: float,
    ) -> SubtitleCueTable | None:
        stmt = select(SubtitleCueTable).where(
            and_(
                SubtitleCueTable.id == cue_id,
                SubtitleCueTable.content_version_id == content_version_id,
                SubtitleCueTable.end_time_seconds <= max_end_time_seconds,
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_adjacent_cues(
        self,
        content_version_id: str,
        ordinal: int,
        max_end_time_seconds: float,
    ) -> list[SubtitleCueTable]:
        stmt = (
            select(SubtitleCueTable)
            .where(
                and_(
                    SubtitleCueTable.content_version_id == content_version_id,
                    SubtitleCueTable.ordinal >= max(0, ordinal - 1),
                    SubtitleCueTable.ordinal <= ordinal + 1,
                    SubtitleCueTable.end_time_seconds <= max_end_time_seconds,
                )
            )
            .order_by(SubtitleCueTable.ordinal.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class StoryFactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_character_fact(
        self,
        content_version_id: str,
        movie_id: str,
        character_name: str,
        fact: str,
        first_known_at_seconds: float,
        relationship: str | None = None,
    ) -> StoryFactTable:
        entry = StoryFactTable(
            id=str(uuid.uuid4()),
            content_version_id=content_version_id,
            movie_id=movie_id,
            character_name=character_name,
            fact=fact,
            relationship_description=relationship,
            first_known_at_seconds=first_known_at_seconds,
            validation_status="verified",
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_character_facts(
        self,
        content_version_id: str,
        max_boundary_seconds: float,
    ) -> list[StoryFactTable]:
        query = (
            select(StoryFactTable)
            .where(
                and_(
                    StoryFactTable.content_version_id == content_version_id,
                    StoryFactTable.character_name.is_not(None),
                    StoryFactTable.first_known_at_seconds <= max_boundary_seconds,
                    StoryFactTable.validation_status == "verified",
                )
            )
            .order_by(
                StoryFactTable.character_name.asc(),
                StoryFactTable.first_known_at_seconds.asc(),
                StoryFactTable.id.asc(),
            )
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
        initial_position: float | None = None,
        progress_source: ProgressSource = ProgressSource.UNKNOWN,
        source: ProgressSource | None = None,
        spoiler_mode: SpoilerMode = SpoilerMode.SAFE,
        session_id: str | None = None,
    ) -> ViewingSessionTable:
        actual_pos = initial_position if initial_position is not None else current_position_seconds
        actual_source = source if source is not None else progress_source
        session_obj = ViewingSessionTable(
            id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            movie_id=movie_id,
            current_position_seconds=max(0.0, actual_pos),
            progress_source=actual_source.value,
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

    async def set_spoiler_confirmation_nonce(self, session_id: str, expire_seconds: int = 300) -> str:
        nonce = secrets.token_urlsafe(24)
        expires_at = datetime.now(UTC) + timedelta(seconds=expire_seconds)
        await self.issue_spoiler_nonce(session_id, nonce, expires_at)
        return nonce

    async def consume_spoiler_confirmation_nonce(self, session_id: str, nonce: str) -> bool:
        sess = await self.get_by_id(session_id)
        if not sess or not sess.spoiler_confirmation_nonce:
            return False
        if sess.spoiler_confirmation_nonce != nonce:
            return False
        now = datetime.now(UTC)
        if sess.spoiler_nonce_expires_at:
            exp = sess.spoiler_nonce_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp < now:
                return False


        sess.spoiler_mode = SpoilerMode.FULL.value
        sess.full_spoilers_confirmed = True
        sess.spoiler_confirmation_nonce = None
        sess.spoiler_nonce_expires_at = None
        await self.session.flush()
        return True

    async def confirm_spoiler_mode(self, session_id: str, nonce: str) -> ViewingSessionTable:
        success = await self.consume_spoiler_confirmation_nonce(session_id, nonce)
        if not success:
            raise ConflictError("Invalid or expired spoiler confirmation token")
        sess = await self.get_by_id(session_id)
        assert sess is not None
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

    async def revert_to_safe_mode(self, session_id: str) -> ViewingSessionTable:
        return await self.reset_to_safe_mode(session_id)

    async def delete_session(self, session_id: str) -> None:
        sess = await self.get_by_id(session_id)
        if sess:
            await self.session.delete(sess)
            await self.session.flush()


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_question(
        self,
        session_id: str,
        movie_id: str,
        question_text: str,
        playback_position_seconds: float,
        user_id: str = "anonymous",
        spoiler_mode: str | None = None,
        spoiler_mode_applied: SpoilerMode | str | None = None,
        status: QuestionStatus | str = "answered",
        request_id: str | None = None,
        answer_text: str | None = None,
    ) -> QuestionTable:
        mode = spoiler_mode_applied or spoiler_mode or "safe"
        actual_mode = mode.value if isinstance(mode, SpoilerMode) else mode
        actual_status = status.value if isinstance(status, QuestionStatus) else status
        q = QuestionTable(
            id=str(uuid.uuid4()),
            session_id=session_id,
            movie_id=movie_id,
            question_text=question_text,
            request_id=request_id or str(uuid.uuid4()),
            playback_position_seconds=playback_position_seconds,
            spoiler_mode=actual_mode,
            status=actual_status,
            answer_text=answer_text,
        )
        self.session.add(q)
        await self.session.flush()
        return q

    async def update_question_status(
        self,
        question_id: str,
        status: QuestionStatus | str,
        answer_text: str | None = None,
    ) -> QuestionTable | None:
        query = select(QuestionTable).where(QuestionTable.id == question_id)
        q = (await self.session.execute(query)).scalars().first()
        if q:
            q.status = status.value if isinstance(status, QuestionStatus) else status
            if answer_text is not None:
                q.answer_text = answer_text
            await self.session.flush()
        return q

    async def link_citation(
        self,
        question_id: str,
        chunk_id: str,
        relevance_score: float = 1.0,
    ) -> AnswerSourceTable:
        sources = [
            AnswerSourceTable(
                id=str(uuid.uuid4()),
                question_id=question_id,
                chunk_id=chunk_id,
                relevance_score=relevance_score,
            )
        ]
        self.session.add_all(sources)
        await self.session.flush()
        return sources[0]

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
        action: AuditAction | str,
        target_id: str,
        user_id: str | None = None,
        actor: str | None = None,
        target_type: str = "session",
        correlation_id: str | None = None,
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEventTable:
        actual_action = action.value if hasattr(action, "value") else str(action)
        actual_actor = actor or user_id or "system"
        actual_corr = correlation_id or str(uuid.uuid4())
        actual_meta = details or metadata
        event = AuditEventTable(
            id=str(uuid.uuid4()),
            actor=actual_actor,
            action=actual_action,
            target_type=target_type,
            target_id=target_id,
            correlation_id=actual_corr,
            metadata_json=json.dumps(actual_meta) if actual_meta else None,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(
        self,
        target_id: str | None = None,
        action: AuditAction | str | None = None,
        limit: int = 50,
    ) -> list[AuditEventTable]:
        """Query audit event trail by target_id or action."""
        stmt = select(AuditEventTable)
        if target_id:
            stmt = stmt.where(AuditEventTable.target_id == target_id)
        if action:
            act_val = action.value if hasattr(action, "value") else str(action)
            stmt = stmt.where(AuditEventTable.action == act_val)
        stmt = stmt.order_by(AuditEventTable.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class MediaAssetRepository:
    """Repository for managing media binary assets (videos, streams, audio)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        movie_id: str,
        asset_type: MediaAssetType | str,
        storage_path: str,
        stream_url: str | None = None,
        duration_seconds: float | None = None,
        file_size_bytes: int | None = None,
        codec: str | None = None,
        status: MediaAssetStatus | str = MediaAssetStatus.PENDING,
        asset_id: str | None = None,
    ) -> MediaAssetTable:
        type_val = asset_type.value if hasattr(asset_type, "value") else str(asset_type)
        status_val = status.value if hasattr(status, "value") else str(status)
        asset = MediaAssetTable(
            id=asset_id or str(uuid.uuid4()),
            movie_id=movie_id,
            asset_type=type_val,
            storage_path=storage_path,
            stream_url=stream_url,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size_bytes,
            codec=codec,
            status=status_val,
        )
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def get_by_id(self, asset_id: str) -> MediaAssetTable | None:
        stmt = select(MediaAssetTable).where(MediaAssetTable.id == asset_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_movie(self, movie_id: str) -> list[MediaAssetTable]:
        stmt = (
            select(MediaAssetTable)
            .where(MediaAssetTable.movie_id == movie_id)
            .order_by(MediaAssetTable.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        asset_id: str,
        status: MediaAssetStatus | str,
        stream_url: str | None = None,
        duration_seconds: float | None = None,
        codec: str | None = None,
    ) -> MediaAssetTable:
        asset = await self.get_by_id(asset_id)
        if not asset:
            raise NotFoundError(f"MediaAsset {asset_id} not found")
        asset.status = status.value if hasattr(status, "value") else str(status)
        if stream_url is not None:
            asset.stream_url = stream_url
        if duration_seconds is not None:
            asset.duration_seconds = duration_seconds
        if codec is not None:
            asset.codec = codec
        await self.session.flush()
        return asset


class ProcessingJobRepository:
    """Repository for tracking asynchronous media processing workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        movie_id: str,
        stage: ProcessingJobStage | str = ProcessingJobStage.UPLOADED,
        job_id: str | None = None,
        max_attempts: int = 3,
    ) -> ProcessingJobTable:
        stage_val = stage.value if hasattr(stage, "value") else str(stage)
        job = ProcessingJobTable(
            id=job_id or str(uuid.uuid4()),
            movie_id=movie_id,
            stage=stage_val,
            attempts=0,
            max_attempts=max_attempts,
            is_retryable=True,
            is_playback_ready=False,
            is_ai_ready=False,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: str) -> ProcessingJobTable | None:
        stmt = select(ProcessingJobTable).where(ProcessingJobTable.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_latest_for_movie(self, movie_id: str) -> ProcessingJobTable | None:
        stmt = (
            select(ProcessingJobTable)
            .where(ProcessingJobTable.movie_id == movie_id)
            .order_by(ProcessingJobTable.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_stage(
        self,
        job_id: str,
        stage: ProcessingJobStage | str,
        is_playback_ready: bool | None = None,
        is_ai_ready: bool | None = None,
    ) -> ProcessingJobTable:
        job = await self.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"ProcessingJob {job_id} not found")
        job.stage = stage.value if hasattr(stage, "value") else str(stage)
        if is_playback_ready is not None:
            job.is_playback_ready = is_playback_ready
        if is_ai_ready is not None:
            job.is_ai_ready = is_ai_ready
        await self.session.flush()
        return job

    async def mark_failed(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        is_retryable: bool = True,
    ) -> ProcessingJobTable:
        job = await self.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"ProcessingJob {job_id} not found")
        job.stage = ProcessingJobStage.FAILED.value
        job.error_code = error_code
        job.error_message = error_message
        job.is_retryable = is_retryable
        job.attempts += 1
        await self.session.flush()
        return job

