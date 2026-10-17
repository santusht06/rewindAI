"""RAG Orchestration engine enforcing server-side spoiler policy, temporal boundaries, and citation validation.

Adheres strictly to:
- SRS-SPO-001 through SRS-SPO-006 (Server spoiler policy, pre-LLM filtering, adversarial defense)
- BE-AI-001 through BE-AI-010 (Hybrid retrieval, grounded answers, citation verification)
- BE-SAFE-001 through BE-SAFE-010 (Single-use nonce flow, boundary integrity)
- AC-004, AC-007, AC-009, AC-010
"""

from datetime import datetime, timezone
import re
from typing import Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.api.schemas import CitationSchema, QuestionResponse
from services.api.ai.provider import ModelProvider, get_model_provider
from services.api.ai.retriever import SubtitleRetriever
from services.api.domain.models import (
    AuditEventAction,
    QuestionStatus,
    SpoilerMode,
)
from services.api.errors import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    QuestionRepository,
    ViewingSessionRepository,
)


class RagOrchestrator:
    """Orchestrates story Q&A retrieval, spoiler gating, and model generation."""

    def __init__(
        self,
        db_session: AsyncSession,
        model_provider: ModelProvider | None = None,
    ) -> None:
        self.session = db_session
        self.movie_repo = MovieRepository(db_session)
        self.version_repo = ContentVersionRepository(db_session)
        self.session_repo = ViewingSessionRepository(db_session)
        self.question_repo = QuestionRepository(db_session)
        self.audit_repo = AuditEventRepository(db_session)
        self.retriever = SubtitleRetriever(db_session)
        self.model_provider = model_provider or get_model_provider()

    async def answer_question(
        self,
        session_id: str,
        question_text: str,
        user_id: str,
        client_request_id: str | None = None,
    ) -> QuestionResponse:
        """Process a question through retrieval and spoiler guardrails."""
        now = datetime.now(timezone.utc)

        # 1. Fetch and validate session
        sess = await self.session_repo.get_by_id(session_id)
        if not sess:
            raise NotFoundError(f"Viewing session '{session_id}' not found.")

        if sess.user_id != user_id:
            raise AuthorizationError("You do not have permission to ask questions in this viewing session.")

        # 2. Fetch and validate movie
        movie = await self.movie_repo.get_by_id(sess.movie_id)
        if not movie:
            raise NotFoundError("Movie associated with this viewing session was not found.")

        # 3. Check active indexed version
        active_version = await self.version_repo.get_active_version(movie.id)
        spoiler_mode_str = sess.spoiler_mode if isinstance(sess.spoiler_mode, str) else sess.spoiler_mode.value
        is_safe_mode = spoiler_mode_str == SpoilerMode.SAFE.value

        if not active_version:
            # Title has no active index (04_API_CONTRACT: unsupported_title)
            return QuestionResponse(
                question_id=str(uuid.uuid4()),
                session_id=sess.id,
                outcome="unsupported_title",
                answer="AI story companion is not currently indexed for this title.",
                citations=[],
                policy_state=spoiler_mode_str,
                created_at=now,
            )

        # 4. Create initial Question record in database
        question_record = await self.question_repo.create_question(
            session_id=sess.id,
            movie_id=movie.id,
            user_id=user_id,
            question_text=question_text,
            playback_position_seconds=sess.current_position_seconds,
            spoiler_mode_applied=spoiler_mode_str,
            status=QuestionStatus.RECEIVED,
            request_id=client_request_id,
        )

        # 5. Detect future spoiler questions in SAFE mode (SRS-SPO-004, AC-009)
        lower_q = question_text.lower()
        future_patterns = [
            r"\bwhat happens next\b",
            r"\bhow does it end\b",
            r"\bwho dies at the end\b",
            r"\bspoiler\b",
            r"\bfuture\b",
            r"\blater in the movie\b",
            r"\bend of the film\b",
        ]
        is_asking_future = any(re.search(p, lower_q) for p in future_patterns)

        if is_safe_mode and is_asking_future:
            # Issue single-use spoiler confirmation nonce
            nonce = await self.session_repo.set_spoiler_confirmation_nonce(sess.id)
            await self.question_repo.update_question_status(
                question_record.id,
                QuestionStatus.SPOILER_CONFIRMATION_REQUIRED,
            )

            await self.audit_repo.record_event(
                action=AuditEventAction.QUESTION_SUBMIT,
                target_id=question_record.id,
                user_id=user_id,
                details={
                    "outcome": "spoiler_confirmation_required",
                    "position": sess.current_position_seconds,
                },
            )

            return QuestionResponse(
                question_id=question_record.id,
                session_id=sess.id,
                outcome="spoiler_confirmation_required",
                answer=(
                    f"Answering this question involves events that occur after your current playback "
                    f"position ({int(sess.current_position_seconds)}s). Safe mode is active to prevent "
                    f"spoilers. Confirm below if you would like full spoilers."
                ),
                citations=[],
                confirmation_nonce=nonce,
                policy_state=spoiler_mode_str,
                created_at=now,
            )

        # 6. Pre-retrieval temporal boundary calculation (AC-004, BE-AI-002)
        max_boundary = (
            sess.current_position_seconds
            if is_safe_mode
            else movie.duration_seconds
        )

        # 7. Execute bounded candidate retrieval
        candidates = await self.retriever.retrieve_candidates(
            content_version_id=active_version.id,
            query=question_text,
            max_boundary_seconds=max_boundary,
            limit=5,
        )

        if not candidates:
            # Safe abstention (BE-AI-007)
            await self.question_repo.update_question_status(
                question_record.id,
                QuestionStatus.INSUFFICIENT_EVIDENCE,
            )
            return QuestionResponse(
                question_id=question_record.id,
                session_id=sess.id,
                outcome="insufficient_evidence",
                answer="No relevant dialogue or scene details have occurred yet up to your current playback position.",
                citations=[],
                policy_state=spoiler_mode_str,
                created_at=now,
            )

        # 8. Call Model Provider with bounded context
        model_output = await self.model_provider.generate_grounded_answer(
            question=question_text,
            context_chunks=candidates,
            playback_position_seconds=sess.current_position_seconds,
            spoiler_mode=spoiler_mode_str,
        )

        outcome = model_output.get("outcome", "answered")
        raw_answer = model_output.get("answer")
        cited_ids = model_output.get("cited_chunk_ids", [])

        # 9. Citation Verification (BE-AI-006): Ensure cited chunks exist in retrieved boundary set
        valid_chunk_map = {c["id"]: c for c in candidates}
        verified_citations: list[CitationSchema] = []

        for cid in cited_ids:
            if cid in valid_chunk_map:
                c = valid_chunk_map[cid]
                verified_citations.append(
                    CitationSchema(
                        chunk_id=c["id"],
                        start_time_seconds=int(c["start_time_seconds"]),
                        end_time_seconds=int(c["end_time_seconds"]),
                        text=c["text"],
                        relevance_score=c.get("relevance_score", 1.0),
                    )
                )

        # If model failed to cite but answered, backfill from top candidate
        if not verified_citations and outcome == "answered" and candidates:
            top_c = candidates[0]
            verified_citations.append(
                CitationSchema(
                    chunk_id=top_c["id"],
                    start_time_seconds=int(top_c["start_time_seconds"]),
                    end_time_seconds=int(top_c["end_time_seconds"]),
                    text=top_c["text"],
                    relevance_score=top_c.get("relevance_score", 1.0),
                )
            )

        # 10. Update Question Status and link citations in database
        status_enum = (
            QuestionStatus.ANSWERED
            if outcome == "answered"
            else QuestionStatus.INSUFFICIENT_EVIDENCE
        )
        await self.question_repo.update_question_status(
            question_id=question_record.id,
            status=status_enum,
            answer_text=raw_answer,
        )

        for cit in verified_citations:
            await self.question_repo.link_citation(
                question_id=question_record.id,
                chunk_id=cit.chunk_id,
                relevance_score=cit.relevance_score,
            )

        await self.audit_repo.record_event(
            action=AuditEventAction.QUESTION_SUBMIT,
            target_id=question_record.id,
            user_id=user_id,
            details={
                "outcome": outcome,
                "position": sess.current_position_seconds,
                "spoiler_mode": spoiler_mode_str,
                "citation_count": len(verified_citations),
            },
        )

        return QuestionResponse(
            question_id=question_record.id,
            session_id=sess.id,
            outcome=outcome,
            answer=raw_answer,
            citations=verified_citations,
            clarification_prompt=model_output.get("clarification_prompt"),
            policy_state=spoiler_mode_str,
            created_at=now,
        )
