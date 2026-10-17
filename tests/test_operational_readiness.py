"""Operational Readiness, Telemetry, Rate Limiting, and Disaster Recovery Test Suite.

Validates:
- OPS-001, OPS-004: Telemetry registry, percentiles, token/cost accounting, and /health/metrics
- OPS-003: Rate limiter sliding window enforcement (HTTP 429 Too Many Requests)
- OPS-005, NFR-DR-001: Verifiable SQLite backup, cryptographic SHA-256 checksums, and recovery
- OPS-006, AC-016: Admin title unpublishing, content version deactivation, and rights revocation
"""

from pathlib import Path
import pytest
import pytest_asyncio
import sqlite3
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ops.scripts.backup_restore import (
    calculate_sha256,
    create_backup,
    restore_backup,
    verify_sqlite_integrity,
)
from services.api.api.dependencies import get_db
from services.api.domain.models import AuditAction, MovieStatus, ProgressSource
from services.api.infrastructure.repositories import (
    AuditEventRepository,
    ContentVersionRepository,
    MovieRepository,
    ViewingSessionRepository,
)
from services.api.infrastructure.tables import Base
from services.api.main import create_app
from services.api.rate_limiting import SlidingWindowRateLimiter, limiter
from services.api.telemetry import telemetry


@pytest_asyncio.fixture
async def test_db_session():
    """In-memory SQLite async database engine for isolated test execution."""
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
    """Async HTTP client configured with test database session."""
    app = create_app()

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_health_metrics_endpoint(api_client: AsyncClient):
    """OPS-001, OPS-004: Verify /health/metrics returns structured telemetry."""
    telemetry.reset()
    telemetry.record_latency("test_operation", 45.0)
    telemetry.record_latency("test_operation", 55.0)
    telemetry.record_latency("test_operation", 65.0)
    telemetry.record_outcome("test_success")
    telemetry.record_token_usage(prompt_tokens=100, completion_tokens=25, cost_usd=0.00015)

    res = await api_client.get("/health/metrics")
    assert res.status_code == 200
    data = res.json()

    assert "total_requests" in data
    assert "latencies_ms" in data
    assert "tokens" in data
    assert "estimated_cost_usd" in data
    assert data["tokens"]["prompt_tokens"] >= 100
    assert data["tokens"]["completion_tokens"] >= 25
    assert data["tokens"]["total_tokens"] >= 125
    assert data["latencies_ms"]["p50"]["test_operation"] == 55.0
    assert data["latencies_ms"]["p95"]["test_operation"] >= 55.0

    # Also test /metrics alias
    alias_res = await api_client.get("/metrics")
    assert alias_res.status_code == 200
    assert alias_res.json()["tokens"]["total_tokens"] == data["tokens"]["total_tokens"]


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_unit():
    """OPS-003: Verify sliding-window rate limiter rejects excessive queries with 429 detail."""
    unit_limiter = SlidingWindowRateLimiter()
    key = "test_user_key"

    # Allow up to 3 requests per 60 seconds
    allowed1, retry1 = unit_limiter.is_allowed(key, max_requests=3, window_seconds=60)
    allowed2, retry2 = unit_limiter.is_allowed(key, max_requests=3, window_seconds=60)
    allowed3, retry3 = unit_limiter.is_allowed(key, max_requests=3, window_seconds=60)

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is True
    assert retry1 == 0

    # 4th request must be rejected
    allowed4, retry4 = unit_limiter.is_allowed(key, max_requests=3, window_seconds=60)
    assert allowed4 is False
    assert retry4 > 0


@pytest.mark.asyncio
async def test_route_rate_limiting_enforcement(api_client: AsyncClient, test_db_session: AsyncSession):
    """OPS-003: Rapid question bursts trigger 429 Too Many Requests."""
    limiter.reset()

    # 1. Setup movie and session
    movie_repo = MovieRepository(test_db_session)
    session_repo = ViewingSessionRepository(test_db_session)

    movie = await movie_repo.create_movie(
        title="Dune: Part Two",
        display_title="Dune: Part Two",
        year=2024,
        duration_seconds=9900,
        status=MovieStatus.PUBLISHED,
    )
    sess = await session_repo.create_session(
        user_id="rate_limited_viewer",
        movie_id=movie.id,
        initial_position=1200.0,
        source=ProgressSource.MANUAL_SLIDER,
    )
    await test_db_session.commit()

    # Pre-exhaust the limiter for this user/endpoint
    endpoint_key = f"/api/v1/sessions/{sess.id}/questions:user:rate_limited_viewer"
    for _ in range(60):
        limiter.is_allowed(key=endpoint_key, max_requests=60, window_seconds=60)

    # The 61st request over the HTTP endpoint must return 429
    res = await api_client.post(
        f"/api/v1/sessions/{sess.id}/questions",
        json={"question": "What is Paul's prophecy?"},
        headers={"x-user-id": "rate_limited_viewer"},
    )
    assert res.status_code == 429
    err = res.json()
    assert err["code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after_seconds" in err["details"]

    limiter.reset()


@pytest.mark.asyncio
async def test_admin_unpublish_and_rights_revocation(
    api_client: AsyncClient, test_db_session: AsyncSession
):
    """OPS-006, AC-016: Instant content unpublishing deactivates versions and prevents questions."""
    movie_repo = MovieRepository(test_db_session)
    content_repo = ContentVersionRepository(test_db_session)
    session_repo = ViewingSessionRepository(test_db_session)
    audit_repo = AuditEventRepository(test_db_session)

    # 1. Create and publish movie with active version
    movie = await movie_repo.create_movie(
        title="Oppenheimer",
        display_title="Oppenheimer",
        year=2023,
        duration_seconds=10800,
        status=MovieStatus.PUBLISHED,
    )
    version = await content_repo.create_version(
        movie_id=movie.id,
        source_type="srt",
        source_hash="sha256_mock_oppenheimer",
        version_number=1,
    )
    await content_repo.publish_version(version.id)

    sess = await session_repo.create_session(
        user_id="viewer_oppenheimer",
        movie_id=movie.id,
        initial_position=1500.0,
        source=ProgressSource.MANUAL_SLIDER,
    )
    await test_db_session.commit()

    # 2. Invoke Admin Unpublish API
    unpublish_res = await api_client.post(
        f"/api/v1/admin/titles/{movie.id}/unpublish",
        headers={"X-Admin-Token": "valid-admin-token"},
    )
    assert unpublish_res.status_code == 200
    assert unpublish_res.json()["status"] == "draft"

    # 3. Verify database state
    refreshed_movie = await movie_repo.get_by_id(movie.id)
    assert refreshed_movie is not None
    assert refreshed_movie.status == MovieStatus.DRAFT.value

    active_ver = await content_repo.get_active_version(movie.id)
    assert active_ver is None  # No version should be active

    # 4. Verify audit event was logged
    audit_events = await audit_repo.list_events(target_id=movie.id)
    unpublish_events = [e for e in audit_events if e.action == AuditAction.UNPUBLISH.value]
    assert len(unpublish_events) >= 1

    # 5. Asking questions on the unpublished title returns unsupported_title
    q_res = await api_client.post(
        f"/api/v1/sessions/{sess.id}/questions",
        json={"question": "Who is Leslie Groves?"},
        headers={"x-user-id": "viewer_oppenheimer"},
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["outcome"] == "unsupported_title"


def test_disaster_recovery_backup_and_restore(tmp_path: Path):
    """OPS-005, NFR-DR-001: Verifiable SQLite backup, checksum validation, and restore."""
    db_file = tmp_path / "source_test.db"
    backup_dir = tmp_path / "backups"
    restore_target = tmp_path / "restored.db"

    # 1. Create and populate SQLite test database
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test_movies (id TEXT PRIMARY KEY, title TEXT);")
    cursor.execute("INSERT INTO test_movies VALUES ('m1', 'Arrival'), ('m2', 'Blade Runner 2049');")
    conn.commit()
    conn.close()

    # 2. Create backup
    backup_file, manifest_file = create_backup(db_path=db_file, output_dir=backup_dir)
    assert backup_file.exists()
    assert manifest_file.exists()
    assert verify_sqlite_integrity(backup_file) is True

    # 3. Verify SHA-256 calculation
    actual_hash = calculate_sha256(backup_file)
    assert len(actual_hash) == 64

    # 4. Restore backup to target
    success = restore_backup(
        backup_path=backup_file,
        target_path=restore_target,
        manifest_path=manifest_file,
    )
    assert success is True
    assert restore_target.exists()
    assert verify_sqlite_integrity(restore_target) is True

    # 5. Verify records in restored target
    r_conn = sqlite3.connect(str(restore_target))
    r_cursor = r_conn.cursor()
    r_cursor.execute("SELECT COUNT(*) FROM test_movies;")
    count = r_cursor.fetchone()[0]
    r_conn.close()
    assert count == 2

    # 6. Tamper detection: modifying manifest hash must trigger error
    tampered_manifest = tmp_path / "tampered.json"
    tampered_manifest.write_text('{"sha256_checksum": "bad_hash_1234567890"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Cryptographic checksum mismatch"):
        restore_backup(
            backup_path=backup_file,
            target_path=tmp_path / "should_fail.db",
            manifest_path=tampered_manifest,
        )
