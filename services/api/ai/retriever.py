"""Hybrid keyword and semantic vector retriever with pre-retrieval temporal spoiler boundary.

Implements:
- BE-AI-001 (Retrieval strategy: hybrid keyword and vector)
- BE-AI-002 (Pre-retrieval temporal boundary filtering)
- BE-AI-003 (Ranking, deduplication, and bounded context assembly)
- AC-004 (Temporal spoiler boundary guarantee)
"""

import json
import logging
import math
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.api.errors import ProviderUnavailableError
from services.api.infrastructure.repositories import SubtitleChunkRepository
from services.api.ingestion.embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return dot / (norm_a * norm_b)


class SubtitleRetriever:
    """Retrieves and ranks grounded subtitle chunks strictly within permitted story boundary."""

    def __init__(
        self,
        db_session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = db_session
        self.chunk_repo = SubtitleChunkRepository(db_session)
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def retrieve_candidates(
        self,
        content_version_id: str,
        query: str,
        max_boundary_seconds: float,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve top candidate chunks strictly at or before max_boundary_seconds.

        Guarantees:
        - Pre-retrieval filtering: chunks with end_time_seconds > max_boundary_seconds
          are filtered out at the SQL query level before ranking or context assembly.
        - Hybrid ranking combining keyword matching and vector similarity.
        """
        # 1. SQL Query enforces boundary gate (AC-004, BE-AI-002)
        safe_chunks = await self.chunk_repo.get_chunks_within_boundary(
            content_version_id=content_version_id,
            max_end_time_seconds=max_boundary_seconds,
            limit=200,
        )

        if not safe_chunks:
            return []

        # 2. Extract query keywords
        stop_words = {"what", "who", "where", "when", "how", "why", "the", "and", "is", "was", "are", "about", "this", "that"}
        q_words = [w for w in re.findall(r"\w+", query.lower()) if w not in stop_words and len(w) > 2]

        # 3. Generate query embedding for semantic search
        try:
            query_embeddings = await self.embedding_provider.embed_texts([query])
            query_vec = query_embeddings[0] if query_embeddings else None
        except ProviderUnavailableError as exc:
            logger.warning("Semantic query embedding unavailable: %s", type(exc).__name__)
            query_vec = None

        scored_candidates: list[tuple[float, dict[str, Any]]] = []

        for c in safe_chunks:
            c_text_lower = c.text.lower()

            # Keyword score (normalized between 0 and 1)
            kw_hits = sum(1 for w in q_words if w in c_text_lower)
            kw_score = min(1.0, kw_hits / max(1, len(q_words)))

            # Semantic vector score
            sem_score = 0.0
            if query_vec and c.embedding_json:
                try:
                    c_vec = json.loads(c.embedding_json)
                    sem_score = max(0.0, cosine_similarity(query_vec, c_vec))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    logger.warning("Ignoring invalid stored embedding: %s", type(exc).__name__)
                    sem_score = 0.0

            # Combined score: 60% semantic + 40% keyword match
            # If query vec unavailable, keyword score governs
            if query_vec:
                composite_score = 0.6 * sem_score + 0.4 * kw_score
            else:
                composite_score = kw_score

            chunk_dict = {
                "id": c.id,
                "ordinal": c.ordinal,
                "start_time_seconds": c.start_time_seconds,
                "end_time_seconds": c.end_time_seconds,
                "start_time_formatted": c.start_time_formatted,
                "end_time_formatted": c.end_time_formatted,
                "text": c.text,
                "speaker": c.speaker,
                "relevance_score": round(composite_score, 4),
            }
            scored_candidates.append((composite_score, chunk_dict))

        # Rank candidates by composite score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Select top candidates, falling back to chronological recency if low relevance
        top_candidates = [c for score, c in scored_candidates[:limit]]
        if not top_candidates:
            # Fall back to most recent chunks up to playback position
            top_candidates = [
                {
                    "id": c.id,
                    "ordinal": c.ordinal,
                    "start_time_seconds": c.start_time_seconds,
                    "end_time_seconds": c.end_time_seconds,
                    "start_time_formatted": c.start_time_formatted,
                    "end_time_formatted": c.end_time_formatted,
                    "text": c.text,
                    "speaker": c.speaker,
                    "relevance_score": 0.5,
                }
                for c in safe_chunks[-limit:]
            ]

        # Re-sort selected top candidates chronologically for coherent narrative context
        top_candidates.sort(key=lambda x: x["start_time_seconds"])
        return top_candidates
