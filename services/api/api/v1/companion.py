"""Viewer endpoints for bounded subtitle translation and character facts."""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.ai.provider import get_model_provider
from services.api.api.dependencies import get_current_user_id, get_db
from services.api.api.schemas import (
    CharacterCardSchema,
    CharacterCardsResponse,
    CharacterFactResponse,
    SubtitleLineSchema,
    SubtitleLineSearchResponse,
    TranslationCitationSchema,
    TranslationRequest,
    TranslationResponse,
)
from services.api.domain.models import SpoilerMode
from services.api.errors import AuthorizationError, NotFoundError, ValidationError
from services.api.infrastructure.repositories import (
    ContentVersionRepository,
    MovieRepository,
    StoryFactRepository,
    SubtitleCueRepository,
    ViewingSessionRepository,
)
from services.api.infrastructure.tables import (
    ContentVersionTable,
    MovieTable,
    SubtitleCueTable,
    ViewingSessionTable,
)
from services.api.rate_limiting import RateLimiter

router = APIRouter(prefix="/sessions", tags=["story companion"])
ViewerId = Annotated[str, Depends(get_current_user_id)]
Database = Annotated[AsyncSession, Depends(get_db)]
TranslationRateLimit = Annotated[None, Depends(RateLimiter())]


async def _get_session_context(
    session_id: str, user_id: str, db: AsyncSession
) -> tuple[ViewingSessionTable, MovieTable, ContentVersionTable, float]:
    session = await ViewingSessionRepository(db).get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Viewing session '{session_id}' not found.")
    if session.user_id != user_id:
        raise AuthorizationError("You do not have permission to access this viewing session.")

    movie = await MovieRepository(db).get_by_id(session.movie_id)
    if not movie:
        raise NotFoundError("Movie associated with this viewing session was not found.")
    active_version = await ContentVersionRepository(db).get_active_version(movie.id)
    if not active_version:
        raise NotFoundError("This title does not have an active subtitle index.")

    full_spoilers = (
        session.spoiler_mode == SpoilerMode.FULL.value
        and session.full_spoilers_confirmed
    )
    boundary = (
        float(movie.duration_seconds)
        if full_spoilers
        else session.current_position_seconds
    )
    return session, movie, active_version, boundary


def _line_schema(chunk: SubtitleCueTable) -> SubtitleLineSchema:
    return SubtitleLineSchema(
        cue_id=chunk.id,
        start_time_seconds=int(chunk.start_time_seconds),
        end_time_seconds=int(chunk.end_time_seconds),
        text=chunk.text,
    )


@router.get("/{session_id}/subtitle-lines", response_model=SubtitleLineSearchResponse)
async def search_subtitle_lines(
    session_id: str,
    query: Annotated[str, Query(min_length=2, max_length=120)],
    user_id: ViewerId,
    db: Database,
) -> SubtitleLineSearchResponse:
    """Search only indexed subtitle passages permitted by the active spoiler boundary."""
    _, _, version, boundary = await _get_session_context(session_id, user_id, db)
    normalized_query = query.strip()
    if not normalized_query:
        raise ValidationError("Subtitle search query cannot be blank.")
    cues = await SubtitleCueRepository(db).search_within_boundary(
        content_version_id=version.id,
        query_text=normalized_query,
        max_end_time_seconds=boundary,
    )
    return SubtitleLineSearchResponse(items=[_line_schema(cue) for cue in cues])


@router.post(
    "/{session_id}/translations",
    response_model=TranslationResponse,
)
async def translate_subtitle_line(
    session_id: str,
    body: TranslationRequest,
    user_id: ViewerId,
    db: Database,
    _rate_limit: TranslationRateLimit,
) -> TranslationResponse:
    """Translate one selected indexed subtitle passage with a verified timestamp citation."""
    _, movie, version, boundary = await _get_session_context(session_id, user_id, db)
    cues = SubtitleCueRepository(db)
    selected = await cues.get_cue(body.cue_id, version.id, boundary)
    if not selected:
        raise NotFoundError("The selected subtitle is not available within the current story boundary.")

    surrounding = await cues.get_adjacent_cues(
        version.id, selected.ordinal, boundary
    )
    provider = get_model_provider()
    translated = await provider.translate_subtitle(
        original_text=selected.text,
        source_locale=movie.language,
        target_locale=body.target_locale,
        surrounding_context=[
            chunk.text for chunk in surrounding if chunk.id != selected.id
        ],
        explain_context=body.explain_context,
    )
    citation = TranslationCitationSchema(
        cue_id=selected.id,
        start_time_seconds=int(selected.start_time_seconds),
        end_time_seconds=int(selected.end_time_seconds),
        text=selected.text,
    )
    translation = translated.get("translation")
    if (
        translated.get("outcome") != "translated"
        or not isinstance(translation, str)
        or not translation.strip()
    ):
        message = translated.get("message")
        return TranslationResponse(
            outcome="insufficient_evidence",
            original_text=selected.text,
            target_locale=body.target_locale,
            citation=citation,
            message=(
                message
                if isinstance(message, str) and message.strip()
                else "The selected subtitle could not be translated reliably."
            ),
        )

    explanation = translated.get("contextual_explanation")
    return TranslationResponse(
        outcome="translated",
        original_text=selected.text,
        target_locale=body.target_locale,
        translation=translation.strip(),
        contextual_explanation=(
            explanation.strip()
            if body.explain_context and isinstance(explanation, str) and explanation.strip()
            else None
        ),
        citation=citation,
    )


@router.get("/{session_id}/characters", response_model=CharacterCardsResponse)
async def get_character_cards(
    session_id: str,
    user_id: ViewerId,
    db: Database,
) -> CharacterCardsResponse:
    """Return curated character facts revealed no later than the session's allowed boundary."""
    _, _, version, boundary = await _get_session_context(session_id, user_id, db)
    facts = await StoryFactRepository(db).list_character_facts(version.id, boundary)
    grouped: dict[str, list[CharacterFactResponse]] = defaultdict(list)
    for item in facts:
        if item.character_name:
            name = item.character_name
            grouped[name].append(
                CharacterFactResponse(
                    fact=item.fact,
                    relationship=item.relationship_description,
                    first_known_at_seconds=int(item.first_known_at_seconds),
                )
            )
    return CharacterCardsResponse(
        items=[
            CharacterCardSchema(character_name=name, facts=character_facts)
            for name, character_facts in grouped.items()
        ]
    )
