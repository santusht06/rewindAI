"""Integration coverage for translation and curated spoiler-aware character features."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.api.dependencies import get_db
from services.api.config import settings
from services.api.domain.models import MovieStatus, ProgressSource, SpoilerMode
from services.api.infrastructure.repositories import MovieRepository, ViewingSessionRepository
from services.api.infrastructure.tables import Base
from services.api.ingestion.pipeline import IngestionPipeline
from services.api.main import create_app

SCRIPT_SRT = """1
00:00:10,000 --> 00:00:20,000
COOPER: Earth is dying from the blight. We need to find an exoplanet to save humanity.

2
00:00:30,000 --> 00:00:45,000
BRAND: Professor Brand has been working on the gravity equation for thirty years.

3
00:01:10,000 --> 00:01:25,000
ROMILLY: Miller's planet is next to Gargantua. Every hour on that planet is seven years on Earth.

4
00:02:00,000 --> 00:02:15,000
MANN: The data was faked! There is no surface, only frozen clouds. I cannot die here alone.

5
00:03:00,000 --> 00:03:15,000
COOPER: Murf, it was me! I was your ghost! Love transcended five-dimensional space.
"""


@pytest_asyncio.fixture
async def story_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        app = create_app()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        ) as client:
            movie = await MovieRepository(db).create_movie(
                title_id="story-companion-test",
                display_title="Authorized Demo",
                duration_seconds=10000,
                status=MovieStatus.PUBLISHED,
            )
            ingest = await IngestionPipeline(db).ingest_asset(
                movie_id=movie.id,
                raw_content=SCRIPT_SRT,
                auto_publish=True,
            )
            session = await ViewingSessionRepository(db).create_session(
                movie_id=movie.id,
                user_id="story-viewer",
                initial_position=50,
                source=ProgressSource.MANUAL_SLIDER,
                spoiler_mode=SpoilerMode.SAFE,
            )
            yield client, db, movie, ingest, session
    await engine.dispose()


@pytest.mark.asyncio
async def test_subtitle_line_search_enforces_safe_boundary_and_session_owner(story_client):
    client, _, _, _, session = story_client
    headers = {"X-User-ID": session.user_id}

    visible = await client.get(
        f"/api/v1/sessions/{session.id}/subtitle-lines",
        params={"query": "gravity equation"},
        headers=headers,
    )
    assert visible.status_code == 200
    assert visible.json()["items"]
    assert all(item["end_time_seconds"] <= 50 for item in visible.json()["items"])

    future = await client.get(
        f"/api/v1/sessions/{session.id}/subtitle-lines",
        params={"query": "Murf"},
        headers=headers,
    )
    assert future.status_code == 200
    assert future.json()["items"] == []

    forbidden = await client.get(
        f"/api/v1/sessions/{session.id}/subtitle-lines",
        params={"query": "Earth blight"},
        headers={"X-User-ID": "another-viewer"},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_translation_returns_verified_selected_source_and_abstains(story_client, monkeypatch):
    client, _, _, _, session = story_client
    headers = {"X-User-ID": session.user_id}
    search = await client.get(
        f"/api/v1/sessions/{session.id}/subtitle-lines",
        params={"query": "gravity equation"},
        headers=headers,
    )
    selected = search.json()["items"][0]

    class TranslationProvider:
        async def translate_subtitle(self, **kwargs):
            assert kwargs["source_locale"] == "en"
            assert kwargs["original_text"] == selected["text"]
            assert all("Murf" not in passage for passage in kwargs["surrounding_context"])
            return {
                "outcome": "translated",
                "translation": "समय और गुरुत्वाकर्षण",
                "contextual_explanation": "The line refers to the character's research.",
            }

    monkeypatch.setattr(
        "services.api.api.v1.companion.get_model_provider",
        lambda: TranslationProvider(),
    )
    translated = await client.post(
        f"/api/v1/sessions/{session.id}/translations",
        headers=headers,
        json={"cue_id": selected["cue_id"], "target_locale": "hi"},
    )
    assert translated.status_code == 200
    result = translated.json()
    assert result["outcome"] == "translated"
    assert result["original_text"] == selected["text"]
    assert result["translation"] == "समय और गुरुत्वाकर्षण"
    assert result["citation"]["cue_id"] == selected["cue_id"]
    assert result["citation"]["start_time_seconds"] == selected["start_time_seconds"]

    class AbstainingProvider:
        async def translate_subtitle(self, **kwargs):
            return {
                "outcome": "insufficient_evidence",
                "message": "The dialogue could not be translated reliably.",
            }

    monkeypatch.setattr(
        "services.api.api.v1.companion.get_model_provider",
        lambda: AbstainingProvider(),
    )
    abstained = await client.post(
        f"/api/v1/sessions/{session.id}/translations",
        headers=headers,
        json={"cue_id": selected["cue_id"], "target_locale": "hi"},
    )
    assert abstained.status_code == 200
    assert abstained.json()["outcome"] == "insufficient_evidence"
    assert abstained.json()["translation"] is None
    assert abstained.json()["citation"]["cue_id"] == selected["cue_id"]


@pytest.mark.asyncio
async def test_translation_cannot_select_a_future_cue(story_client):
    client, db, _, ingest, session = story_client
    from services.api.infrastructure.repositories import SubtitleCueRepository

    future_cues = await SubtitleCueRepository(db).search_within_boundary(
        ingest.content_version_id,
        query_text="Murf",
        max_end_time_seconds=10000,
    )
    future = next(cue for cue in future_cues if cue.end_time_seconds > 50)
    response = await client.post(
        f"/api/v1/sessions/{session.id}/translations",
        headers={"X-User-ID": session.user_id},
        json={"cue_id": future.id, "target_locale": "hi"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_curated_character_facts_are_filtered_by_reveal_time(story_client, monkeypatch):
    client, db, movie, _, session = story_client
    monkeypatch.setattr(settings, "admin_api_token", SecretStr("test-admin-token-which-is-long-enough"))
    admin_headers = {"X-Admin-Token": "test-admin-token-which-is-long-enough"}

    early = await client.post(
        f"/api/v1/admin/titles/{movie.id}/character-facts",
        headers=admin_headers,
        json={
            "character_name": "Cooper",
            "fact": "Cooper is Murph's father.",
            "relationship": "Father of Murph.",
            "first_known_at_seconds": 20,
        },
    )
    future = await client.post(
        f"/api/v1/admin/titles/{movie.id}/character-facts",
        headers=admin_headers,
        json={
            "character_name": "Cooper",
            "fact": "Cooper was Murph's ghost.",
            "relationship": "Communicates through the bookshelf.",
            "first_known_at_seconds": 180,
        },
    )
    assert early.status_code == 201
    assert future.status_code == 201

    safe_cards = await client.get(
        f"/api/v1/sessions/{session.id}/characters",
        headers={"X-User-ID": session.user_id},
    )
    assert safe_cards.status_code == 200
    card = safe_cards.json()["items"][0]
    assert card["character_name"] == "Cooper"
    assert len(card["facts"]) == 1
    assert "father" in card["facts"][0]["fact"].lower()

    nonce = await ViewingSessionRepository(db).set_spoiler_confirmation_nonce(session.id)
    confirmation = await client.post(
        f"/api/v1/sessions/{session.id}/spoiler-confirmation",
        headers={"X-User-ID": session.user_id},
        json={"confirmation_nonce": nonce},
    )
    assert confirmation.status_code == 200
    full_cards = await client.get(
        f"/api/v1/sessions/{session.id}/characters",
        headers={"X-User-ID": session.user_id},
    )
    assert len(full_cards.json()["items"][0]["facts"]) == 2
    future_lines = await client.get(
        f"/api/v1/sessions/{session.id}/subtitle-lines",
        params={"query": "Murf"},
        headers={"X-User-ID": session.user_id},
    )
    assert future_lines.json()["items"]


@pytest.mark.asyncio
async def test_companion_routes_are_in_openapi(story_client):
    client, *_ = story_client
    schema = (await client.get("/openapi.json")).json()
    paths = schema["paths"]
    assert "/api/v1/sessions/{session_id}/subtitle-lines" in paths
    assert "/api/v1/sessions/{session_id}/translations" in paths
    assert "/api/v1/sessions/{session_id}/characters" in paths
    assert "/api/v1/admin/titles/{title_id}/character-facts" in paths
