"""Unit tests for configuration management and secret masking.

Verifies NFR-SEC-001 (secrets stored server-side), NFR-PRIV-001 (secret redaction).
"""

import pytest
from pydantic import SecretStr

from services.api.api.dependencies import get_current_user_id
from services.api.config import Settings, settings
from services.api.errors import AppException


def test_settings_default_values() -> None:
    """Verify default development configuration."""
    cfg = Settings()
    assert cfg.app_name == "Rewind AI Companion API"
    assert cfg.environment == "development"
    assert cfg.spoiler_default_mode == "safe"
    assert cfg.max_context_tokens == 4000
    assert not cfg.is_production()


def test_settings_secret_masking() -> None:
    """Ensure secret keys are masked in string representation."""
    secret_val = "very-confidential-api-key-value-12345"
    cfg = Settings(secret_key=SecretStr(secret_val), gemini_api_key=SecretStr(secret_val))

    assert secret_val not in str(cfg.secret_key)
    assert secret_val not in repr(cfg.secret_key)
    assert "**********" in str(cfg.secret_key)
    assert cfg.secret_key.get_secret_value() == secret_val


def test_provider_presence_helpers() -> None:
    """Verify provider configuration detection."""
    cfg_none = Settings(gemini_api_key=None, openai_api_key=None)
    assert not cfg_none.has_gemini_provider()
    assert not cfg_none.has_openai_provider()

    cfg_gemini = Settings(gemini_api_key=SecretStr("mock-key"))
    assert cfg_gemini.has_gemini_provider()


def test_production_viewer_identity_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(AppException) as error:
        get_current_user_id(x_user_id="caller-controlled-user")
    assert error.value.status_code == 503
    assert error.value.code == "AUTHENTICATION_NOT_CONFIGURED"
