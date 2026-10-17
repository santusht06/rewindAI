"""Unit tests for privacy-aware logging and credential redaction.

Verifies NFR-PRIV-001 and Acceptance Scenario AC-020.
"""

from services.api.logging import redact_sensitive_text


def test_redact_bearer_tokens() -> None:
    """Ensure Bearer tokens in headers or logs are redacted."""
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret123"
    sanitized = redact_sensitive_text(raw)
    assert "secret123" not in sanitized
    assert "Bearer [REDACTED]" in sanitized


def test_redact_key_value_secrets() -> None:
    """Ensure passwords and api keys in key-value format are redacted."""
    raw = "Client requested with api_key=sk-ant-api03-abcdef123456 and password='supersecretpassword'"
    sanitized = redact_sensitive_text(raw)
    assert "sk-ant-api03-abcdef123456" not in sanitized
    assert "supersecretpassword" not in sanitized
    assert "api_key=[REDACTED]" in sanitized or "api_key='[REDACTED]'" in sanitized or "[REDACTED]" in sanitized


def test_clean_text_unchanged() -> None:
    """Normal text without credentials should remain untouched."""
    raw = "User asked: 'Who is the mysterious person in the black coat?'"
    sanitized = redact_sensitive_text(raw)
    assert sanitized == raw
