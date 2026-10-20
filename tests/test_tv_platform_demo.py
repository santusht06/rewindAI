"""Test Suite for Fire TV and Vega OS Television Packaging, Manifests, and Live Demo Journey.

Validates:
- PLAT-001, PLAT-002: W3C Television Web App Manifest & Amazon Fire TV / Vega OS configurations
- PLAT-004, PLAT-005: Packaging script integrity, archive generation, and asset verification
- DEMO-001 through DEMO-007: 5-minute live demo user journey repeatability against backend contracts
"""

import zipfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ops.scripts.package_tv_app import (
    calculate_sha256,
    package_tv_app,
    validate_amazon_config,
    validate_manifest,
    validate_tv_client_assets,
)
from services.api.api.dependencies import get_db
from services.api.domain.models import MovieStatus
from services.api.infrastructure.repositories import (
    ContentVersionRepository,
    MovieRepository,
    SubtitleChunkRepository,
)
from services.api.infrastructure.tables import Base
from services.api.main import create_app


@pytest_asyncio.fixture
async def test_db_session():
    """Isolated test database session for TV platform demo testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(test_db_session: AsyncSession):
    """Async HTTP client with test database session override."""
    app = create_app()

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def test_tv_client_asset_completeness():
    """PLAT-002: Verify all required TV assets, styles, scripts, and configurations exist."""
    client_dir = Path("apps/tv-client")
    missing = validate_tv_client_assets(client_dir)
    assert not missing, f"Missing TV assets: {missing}"


def test_w3c_tv_manifest_validation():
    """PLAT-002: Verify W3C Web Application Manifest conforms to 10-ft TV specifications."""
    manifest_path = Path("apps/tv-client/manifest.json")
    data = validate_manifest(manifest_path)
    assert data["display"] == "fullscreen"
    assert data["orientation"] == "landscape"
    assert data["tv"]["spatial_navigation"] is True
    assert data["tv"]["input_mode"] == "dpad"


def test_amazon_webapp_config_validation():
    """PLAT-002: Verify Amazon Web App configuration supports both Fire TV and Vega OS targets."""
    config_path = Path("apps/tv-client/amazon-webapp-config.json")
    data = validate_amazon_config(config_path)
    assert "FireTV" in data["targets"]
    assert "VegaTV" in data["targets"]
    assert data["fullscreen"] is True
    assert data["features"]["dpad_navigation"] is True


def test_package_tv_app_utility(tmp_path: Path):
    """PLAT-004, DEMO-006: Build and verify TV distribution archive and manifest."""
    client_dir = Path("apps/tv-client")
    out_dir = tmp_path / "dist"

    zip_file, manifest_file = package_tv_app(client_dir=client_dir, output_dir=out_dir)

    assert zip_file.exists()
    assert manifest_file.exists()

    # Validate zip contents
    with zipfile.ZipFile(zip_file, "r") as zf:
        namelist = zf.namelist()
        assert "index.html" in namelist
        assert "css/style.css" in namelist
        assert "js/remote.js" in namelist
        assert "js/api.js" in namelist
        assert "manifest.json" in namelist
        assert "amazon-webapp-config.json" in namelist

    # Validate cryptographic hash
    expected_hash = calculate_sha256(zip_file)
    import json
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["sha256_checksum"] == expected_hash
    assert "Amazon Fire OS 7" in manifest_data["target_platforms"]
    assert "Amazon Vega OS" in manifest_data["target_platforms"]


@pytest.mark.asyncio
async def test_demo_script_5min_journey(api_client: AsyncClient, test_db_session: AsyncSession):
    """DEMO-001..005: Execute complete 5-minute live demo script sequence over HTTP contract."""
    movie_repo = MovieRepository(test_db_session)
    content_repo = ContentVersionRepository(test_db_session)
    chunk_repo = SubtitleChunkRepository(test_db_session)

    # 1. Setup Demo Seed Title & Subtitle Index (Interstellar)
    movie = await movie_repo.create_movie(
        title="Interstellar",
        display_title="Interstellar",
        year=2014,
        duration_seconds=10140,
        status=MovieStatus.PUBLISHED,
    )
    version = await content_repo.create_version(
        movie_id=movie.id,
        source_type="srt",
        source_hash="sha256_interstellar_demo_seed",
        version_number=1,
    )
    await chunk_repo.bulk_create([
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 0,
            "start_time_seconds": 120.0,
            "end_time_seconds": 360.0,
            "start_time_formatted": "00:02:00",
            "end_time_formatted": "00:06:00",
            "text": "Cooper wakes up from a crash nightmare. His daughter Murph enters the room.",
            "speaker": "Cooper",
        },
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 1,
            "start_time_seconds": 800.0,
            "end_time_seconds": 960.0,
            "start_time_formatted": "00:13:20",
            "end_time_formatted": "00:16:00",
            "text": "A severe dust storm sweeps through the farm. Cooper and Murph find dust falling in binary lines forming coordinates.",
            "speaker": "Cooper",
        },
        {
            "content_version_id": version.id,
            "movie_id": movie.id,
            "ordinal": 2,
            "start_time_seconds": 9000.0,
            "end_time_seconds": 9800.0,
            "start_time_formatted": "02:30:00",
            "end_time_formatted": "02:43:20",
            "text": "Cooper enters the tesseract black hole Gargantua to transmit quantum data to adult Murph via the watch secondhand.",
            "speaker": "Cooper",
        },
    ])
    await content_repo.publish_version(version.id)
    await test_db_session.commit()

    # Step 1: Health Readiness Probe
    ready_res = await api_client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    # Step 2: Catalog Discovery
    cat_res = await api_client.get("/api/v1/titles")
    assert cat_res.status_code == 200
    items = cat_res.json()["items"]
    assert any(item["display_title"] == "Interstellar" for item in items)

    # Step 3: Session Creation with Playback at 15m 00s (900s)
    sess_res = await api_client.post(
        "/api/v1/sessions",
        json={"title_id": movie.id, "position_seconds": 900.0, "source": "manual_slider"},
        headers={"x-user-id": "demo_operator"},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["session_id"]

    # Step 4: Ask In-Bounds Question (< 900s)
    q1_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What did Cooper find in the dust storm?"},
        headers={"x-user-id": "demo_operator"},
    )
    assert q1_res.status_code == 200
    q1_data = q1_res.json()
    assert q1_data["outcome"] == "answered"
    assert len(q1_data["citations"]) >= 1
    # Verify citations are within current playback bounds (<= 960s)
    assert q1_data["citations"][0]["start_time_seconds"] <= 900.0

    # Step 5: Adversarial Future Spoiler Question (> 900s) in SAFE mode
    q2_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What happens in the black hole at the end of the movie?"},
        headers={"x-user-id": "demo_operator"},
    )
    assert q2_res.status_code == 200
    q2_data = q2_res.json()
    assert q2_data["outcome"] == "spoiler_confirmation_required"
    assert q2_data["confirmation_nonce"] is not None
    nonce = q2_data["confirmation_nonce"]

    # Step 6: Elevate to FULL Spoiler Mode using Nonce
    confirm_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/spoiler-confirmation",
        json={"confirmation_nonce": nonce, "confirmed": True},
        headers={"x-user-id": "demo_operator"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["spoiler_mode"] == "full"

    # Step 7: Re-ask Future Question with FULL Spoilers Permitted
    q3_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What happens in the black hole at the end of the movie?"},
        headers={"x-user-id": "demo_operator"},
    )
    assert q3_res.status_code == 200
    q3_data = q3_res.json()
    assert q3_data["outcome"] == "answered"

    # Step 8: Safe Abstention on Insufficient Evidence
    q4_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/questions",
        json={"question": "What is the recipe for chocolate chip cookies?"},
        headers={"x-user-id": "demo_operator"},
    )
    assert q4_res.status_code == 200
    assert q4_res.json()["outcome"] == "insufficient_evidence"

    # Step 9: Revert to Safe Mode
    safe_res = await api_client.post(
        f"/api/v1/sessions/{session_id}/safe-mode",
        headers={"x-user-id": "demo_operator"},
    )
    assert safe_res.status_code == 200
    assert safe_res.json()["spoiler_mode"] == "safe"

    # Step 10: Session Cleanup
    del_res = await api_client.delete(
        f"/api/v1/sessions/{session_id}",
        headers={"x-user-id": "demo_operator"},
    )
    assert del_res.status_code == 204
