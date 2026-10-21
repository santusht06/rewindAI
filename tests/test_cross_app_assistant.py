"""Automated regression tests for cross-app AI assistant and provider neutrality.

Validates requirements from 17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md:
- Provider-neutral playback context acquisition
- Provider capability registry and empirical status
- Presentation modes and invocation entry points
- Cross-provider switching without breaking core AI logic
- Honest fallback and provenance tracking
"""

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.assistant.contracts import (
    AssistantEntryPoint,
    AssistantPresentationMode,
    ProviderCapabilityStatus,
    StreamingProviderInfo,
)
from services.api.assistant.registry import ProviderCapabilityRegistry, provider_registry
from services.api.main import app


@pytest.mark.asyncio
async def test_provider_capability_registry_defaults():
    """Verify registry contains major providers with honest capability status."""
    registry = ProviderCapabilityRegistry()
    providers = {p.id: p for p in registry.list_providers()}

    # Netflix must be UNAVAILABLE for direct background context sync due to OS container sandbox
    assert "netflix" in providers
    netflix = providers["netflix"]
    assert netflix.name == "Netflix"
    assert netflix.context_sync_status == ProviderCapabilityStatus.UNAVAILABLE
    assert AssistantPresentationMode.SIDE_PANEL_OVERLAY in netflix.supported_presentation_modes

    # Prime Video has PARTIAL capability via Amazon ecosystem
    assert "prime_video" in providers
    prime = providers["prime_video"]
    assert prime.context_sync_status == ProviderCapabilityStatus.PARTIAL

    # Simulator is VERIFIED for local/demo evaluation
    assert "simulator" in providers
    sim = providers["simulator"]
    assert sim.context_sync_status == ProviderCapabilityStatus.VERIFIED


@pytest.mark.asyncio
async def test_get_assistant_providers_endpoint():
    """Verify GET /api/v1/assistant/providers returns all providers and transparent statuses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/assistant/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert data["total"] >= 5

        ids = [p["id"] for p in data["providers"]]
        assert "netflix" in ids
        assert "prime_video" in ids
        assert "disney_plus" in ids
        assert "youtube" in ids
        assert "simulator" in ids


@pytest.mark.asyncio
async def test_get_single_provider_details():
    """Verify GET /api/v1/assistant/providers/{id} returns details or 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid provider
        res_ok = await client.get("/api/v1/assistant/providers/netflix")
        assert res_ok.status_code == 200
        n_data = res_ok.json()
        assert n_data["id"] == "netflix"
        assert n_data["context_sync_status"] == "UNAVAILABLE"
        assert "notes" in n_data

        # Unknown provider
        res_404 = await client.get("/api/v1/assistant/providers/unknown_tv_app")
        assert res_404.status_code == 404
        assert res_404.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_presentation_modes_endpoint():
    """Verify GET /api/v1/assistant/modes returns supported TV surfaces."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/assistant/modes")
        assert response.status_code == 200
        data = response.json()
        assert "SIDE_PANEL_OVERLAY" in data["supported_modes"]
        assert "COMPANION_DEVICE" in data["supported_modes"]
        assert "VOICE_COMMAND" in data["supported_entry_points"]
        assert data["default_mode"] == "SIDE_PANEL_OVERLAY"


@pytest.mark.asyncio
async def test_cross_provider_context_resolution_and_switching():
    """Verify creating a session and seamlessly switching streaming provider context."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session for Interstellar
        session_res = await client.post(
            "/api/v1/sessions",
            json={
                "title_id": "interstellar-epic",
                "position_seconds": 1800,
                "source": "manual_slider",
            },
            headers={"X-User-Id": "viewer_provider_test"},
        )
        assert session_res.status_code == 201
        session_id = session_res.json()["session_id"]

        # 2. Get initial context
        ctx_res1 = await client.get(
            f"/api/v1/assistant/sessions/{session_id}/context",
            headers={"X-User-Id": "viewer_provider_test"},
        )
        assert ctx_res1.status_code == 200
        ctx1 = ctx_res1.json()
        assert ctx1["title_id"] == "interstellar-epic"
        assert ctx1["current_position_seconds"] == 1800

        # 3. Switch context to Netflix at 2100 seconds
        update_res1 = await client.post(
            f"/api/v1/assistant/sessions/{session_id}/context",
            json={
                "provider_id": "netflix",
                "position_seconds": 2100,
                "source": "manual_slider",
            },
            headers={"X-User-Id": "viewer_provider_test"},
        )
        assert update_res1.status_code == 200
        n_ctx = update_res1.json()
        assert n_ctx["provider_id"] == "netflix"
        assert n_ctx["current_position_seconds"] == 2100
        assert n_ctx["is_verified"] is False
        assert "Netflix" in n_ctx["provenance_note"]

        # 4. Switch context to Prime Video with Voice Cue
        update_res2 = await client.post(
            f"/api/v1/assistant/sessions/{session_id}/context",
            json={
                "provider_id": "prime_video",
                "position_seconds": 2400,
                "source": "voice_cue",
            },
            headers={"X-User-Id": "viewer_provider_test"},
        )
        assert update_res2.status_code == 200
        p_ctx = update_res2.json()
        assert p_ctx["provider_id"] == "prime_video"
        assert p_ctx["current_position_seconds"] == 2400
        assert "Voice cue" in p_ctx["provenance_note"]

        # 5. Core Q&A continues to work with updated provider context
        q_res = await client.post(
            f"/api/v1/sessions/{session_id}/questions",
            json={"question": "What is the mission about?"},
            headers={"X-User-Id": "viewer_provider_test"},
        )
        assert q_res.status_code == 200
        assert q_res.json()["outcome"] in ("answered", "insufficient_evidence")


@pytest.mark.asyncio
async def test_unauthorized_session_context_access():
    """Verify cross-user isolation on assistant context endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates session
        res = await client.post(
            "/api/v1/sessions",
            json={"title_id": "interstellar-epic", "position_seconds": 600},
            headers={"X-User-Id": "user_alice"},
        )
        session_id = res.json()["session_id"]

        # User B attempts to read User A's context -> 403 Forbidden
        forbidden_res = await client.get(
            f"/api/v1/assistant/sessions/{session_id}/context",
            headers={"X-User-Id": "user_bob"},
        )
        assert forbidden_res.status_code == 403
        assert forbidden_res.json()["code"] == "FORBIDDEN"

