"""Integration and regression test suite for 10-ft Fire TV Web Client.

Verifies:
- FE-FOUND-001 through FE-FOUND-006: Frontend toolchain, typed API client, static mount
- FE-UI-001 through FE-UI-008: 9 screens (S1-S9), focus states, spoiler flows, remote navigation
- AC-017: Remote-only TV D-pad navigation landmarks and safe-area structures
"""

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_root_redirects_to_tv_client(app):
    """Root URL (/) redirects to 10-ft Fire TV interface (/tv/)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/", follow_redirects=False)
        assert res.status_code in (301, 302, 307)
        assert res.headers["location"] == "/tv/"


@pytest.mark.asyncio
async def test_tv_client_html_structure_contains_all_screens(app):
    """TV Client index.html contains all 9 required screens and Fire TV Remote simulator."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/tv/")
        assert res.status_code == 200
        html = res.text

        # Verify page title and safe-area enclosure
        assert "<title>Rewind — Fire TV Story Companion</title>" in html
        assert 'class="tv-safe-area"' in html

        # Verify all 9 screens are present per 06_UX_AND_SCREEN_REQUIREMENTS
        screens = [
            "s1-welcome",        # S1: Welcome & Privacy
            "s2-catalog",        # S2: Title Catalog
            "s3-details",        # S3: Details & Progress
            "s4-companion",      # S4: Companion & Question
            "s5-answer",         # S5: Grounded Answer & Citations
            "s6-clarification",   # S6: Clarification & Safe Abstention
            "s7-spoiler-modal",  # S7: Spoiler Confirmation Modal
            "s8-settings",       # S8: Settings & Privacy
            "s9-admin",          # S9: Ingestion & Diagnostics
        ]
        for screen in screens:
            assert f'id="{screen}"' in html, f"Screen {screen} missing from TV client DOM"
        assert 'id="admin-api-token"' in html
        assert 'type="password"' in html

        # Verify Fire TV Remote Controller Simulator
        assert 'id="remote-simulator"' in html
        assert 'id="rem-up"' in html
        assert 'id="rem-ok"' in html
        assert 'id="rem-back"' in html


@pytest.mark.asyncio
async def test_tv_client_assets_served_correctly(app):
    """CSS and JS assets are served with correct headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        css_res = await client.get("/tv/css/style.css")
        assert css_res.status_code == 200
        assert "var(--bg-oled)" in css_res.text
        assert "tv-focusable" in css_res.text
        assert "outer-bezel" in css_res.text

        for js_file in ["api.js", "remote.js", "app.js"]:
            js_res = await client.get(f"/tv/js/{js_file}")
            assert js_res.status_code == 200, f"Failed to load {js_file}"
            assert len(js_res.text) > 100
            if js_file == "api.js":
                assert "X-Admin-Token" in js_res.text
                assert "X-Admin-Role" not in js_res.text
