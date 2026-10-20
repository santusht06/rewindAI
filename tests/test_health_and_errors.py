"""Integration tests for health probes, correlation middleware, and error envelopes.

Verifies SRS-ADM-003, NFR-OBS-001, 04_API_CONTRACT error semantics.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from services.api import main as api_main
from services.api.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitExceededError,
)
from services.api.main import create_app


@pytest.mark.asyncio
async def test_database_connectivity_check_queries_database() -> None:
    database_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        assert await api_main.check_database_connectivity(database_engine) is True
    finally:
        await database_engine.dispose()


@pytest.mark.asyncio
async def test_database_connectivity_check_reports_unavailable_database() -> None:
    connection = AsyncMock()
    connection.__aenter__.side_effect = OperationalError("SELECT 1", {}, RuntimeError("failed"))
    database_engine = MagicMock()
    database_engine.connect.return_value = connection

    assert await api_main.check_database_connectivity(database_engine) is False


# Router for testing domain exceptions and errors
dummy_router = APIRouter(prefix="/test")


@dummy_router.get("/not-found")
async def trigger_not_found() -> None:
    raise NotFoundError("The requested title was not found", details={"title_id": "missing-123"})


@dummy_router.get("/unauthorized")
async def trigger_unauthorized() -> None:
    raise AuthorizationError("You do not have permission to access this session")


@dummy_router.get("/conflict")
async def trigger_conflict() -> None:
    raise ConflictError("Session is already in full spoiler mode")


@dummy_router.get("/rate-limited")
async def trigger_rate_limit() -> None:
    raise RateLimitExceededError("Rate limit exceeded for testing", retry_after_seconds=30)


@dummy_router.get("/unhandled-error")
async def trigger_unhandled() -> None:
    raise RuntimeError("Simulated unexpected crash")


@pytest.fixture
def app_with_test_routes():
    test_app = create_app()
    test_app.include_router(dummy_router)
    return test_app


@pytest.mark.asyncio
async def test_health_live_endpoint(app_with_test_routes) -> None:
    """Ensure /health/live returns 200 with status=alive and valid timestamp."""
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "environment" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_ready_endpoint(app_with_test_routes, monkeypatch) -> None:
    """Ensure /health/ready returns 200 with component statuses and no secret leaks."""
    async def database_ready(_database_engine) -> bool:
        return True

    monkeypatch.setattr(api_main, "check_database_connectivity", database_ready)
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "components" in data
        assert data["components"]["config"] == "ready"
        assert data["components"]["persistence"] == "ready"
        # Verify no credentials leaked in body
        assert "secret" not in response.text.lower()
        assert "password" not in response.text.lower()


@pytest.mark.asyncio
async def test_health_ready_fails_closed_when_database_is_unavailable(
    app_with_test_routes, monkeypatch
) -> None:
    """Readiness returns 503 and does not expose database error details."""
    async def database_unavailable(_database_engine) -> bool:
        return False

    monkeypatch.setattr(api_main, "check_database_connectivity", database_unavailable)
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unready"
    assert response.json()["components"] == {
        "config": "ready",
        "persistence": "unavailable",
    }
    assert "password" not in response.text.lower()
    assert "secret" not in response.text.lower()


@pytest.mark.asyncio
async def test_request_id_correlation_header(app_with_test_routes) -> None:
    """Ensure X-Request-ID is generated and returned, or preserved if provided."""
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Case 1: Auto-generated
        resp1 = await client.get("/health/live")
        assert "X-Request-ID" in resp1.headers
        assert resp1.headers["X-Request-ID"].startswith("req_")

        # Case 2: Client-provided propagated
        custom_id = "client-trace-987654"
        resp2 = await client.get("/health/live", headers={"X-Request-ID": custom_id})
        assert resp2.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_error_envelope_not_found(app_with_test_routes) -> None:
    """Ensure NotFoundError returns 404 with standardized ErrorEnvelope."""
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"
        assert "requested title was not found" in data["message"]
        assert "request_id" in data
        assert data["details"]["title_id"] == "missing-123"


@pytest.mark.asyncio
async def test_error_envelope_authorization_error(app_with_test_routes) -> None:
    """Ensure AuthorizationError returns 403 with standardized ErrorEnvelope."""
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/unauthorized")
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "FORBIDDEN"
        assert data["message"] == "You do not have permission to access this session"


@pytest.mark.asyncio
async def test_error_envelope_conflict_error(app_with_test_routes) -> None:
    """Ensure ConflictError returns 409 with standardized ErrorEnvelope."""
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/conflict")
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "STATE_CONFLICT"


@pytest.mark.asyncio
async def test_error_envelope_rate_limit_error(app_with_test_routes) -> None:
    """Ensure RateLimitExceededError returns 429 with retry_after_seconds."""
    transport = ASGITransport(app=app_with_test_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/rate-limited")
        assert response.status_code == 429
        data = response.json()
        assert data["code"] == "RATE_LIMIT_EXCEEDED"
        assert data["details"]["retry_after_seconds"] == 30


@pytest.mark.asyncio
async def test_error_envelope_unhandled_crash(app_with_test_routes) -> None:
    """Ensure unexpected exceptions return 500 without leaking stack traces."""
    transport = ASGITransport(app=app_with_test_routes, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/unhandled-error")
        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected server error" in data["message"]
        # Invariant: Never leak stack traces to client
        assert "traceback" not in response.text.lower()
        assert "RuntimeError" not in response.text
