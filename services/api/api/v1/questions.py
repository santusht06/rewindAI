"""API endpoint for Question submission and spoiler-gated Q&A.

Adheres strictly to:
- SRS-SPO-001 through SRS-SPO-006 (Server-side boundary, pre-LLM filtering, adversarial defense)
- BE-AI-001 through BE-AI-010 (Hybrid retrieval, grounded answers, citation verification)
- 04_API_CONTRACT.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.ai.orchestrator import RagOrchestrator
from services.api.api.dependencies import get_current_user_id, get_db
from services.api.api.schemas import QuestionRequest, QuestionResponse
from services.api.rate_limiting import RateLimiter

router = APIRouter(prefix="/sessions", tags=["questions"])


@router.post("/{session_id}/questions", response_model=QuestionResponse)
async def ask_question(
    session_id: str,
    body: QuestionRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate_limit: Annotated[None, Depends(RateLimiter())],
) -> QuestionResponse:
    """Submit a question within a viewing session.

    Delegates to RagOrchestrator to enforce:
    1. Session existence and viewer ownership.
    2. Server-controlled spoiler policy and playback position.
    3. Pre-retrieval evidence boundary filtering (future chunks are physically excluded).
    4. Single-use nonce flow for future spoiler requests.
    5. Verified citation grounding and safe abstention.
    """
    orchestrator = RagOrchestrator(db_session=db)
    return await orchestrator.answer_question(
        session_id=session_id,
        question_text=body.question,
        user_id=user_id,
        client_request_id=body.client_request_id,
    )
