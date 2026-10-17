"""Standardized error envelope and domain exception hierarchy for Rewind.

Implements SRS-QA-001, 04_API_CONTRACT section 3, NFR-OBS-001.
"""

from typing import Any
from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    """Consistent error response schema across all endpoints."""

    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Safe human-readable error description")
    request_id: str = Field(..., description="Correlation ID for tracing and log correlation")
    details: dict[str, Any] | None = Field(default=None, description="Optional safe structured context")


class AppException(Exception):
    """Base exception for all domain and application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="NOT_FOUND", message=message, status_code=404, details=details)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="UNAUTHENTICATED", message=message, status_code=401, details=details)


class AuthorizationError(AppException):
    def __init__(self, message: str = "Access denied", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403, details=details)


class ConflictError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="STATE_CONFLICT", message=message, status_code=409, details=details)


class PayloadTooLargeError(AppException):
    def __init__(self, message: str = "Request payload exceeds allowed limit", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="PAYLOAD_TOO_LARGE", message=message, status_code=413, details=details)


class RateLimitExceededError(AppException):
    def __init__(self, message: str = "Rate limit exceeded", retry_after_seconds: int = 60) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
            details={"retry_after_seconds": retry_after_seconds},
        )


class ProviderUnavailableError(AppException):
    def __init__(self, message: str = "External AI provider temporarily unavailable", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="PROVIDER_UNAVAILABLE", message=message, status_code=503, details=details)


class ProviderTimeoutError(AppException):
    def __init__(self, message: str = "External AI provider timed out", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="GATEWAY_TIMEOUT", message=message, status_code=504, details=details)
