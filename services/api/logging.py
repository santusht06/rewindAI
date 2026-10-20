"""Privacy-aware structured logging and correlation middleware for Rewind.

Implements NFR-PRIV-001 (log redaction), NFR-OBS-001 (request correlation), and AC-020.
"""

import contextvars
import logging
import re
import sys
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from services.api.telemetry import telemetry

# Context variable for request correlation ID
current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_request_id", default="system-init"
)

# Compiled regex patterns for redaction
AUTH_HEADER_PATTERN = re.compile(r"(\bAuthorization\s*[:=]\s*Bearer\s+)[^\s,]+", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"(\bBearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE)
KEY_VALUE_SECRET_PATTERN = re.compile(
    r'(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*["\']?([^"\'\s,]+)'
)


def redact_sensitive_text(text: str) -> str:
    """Sanitize secrets, tokens, and credentials from log messages."""
    if not text:
        return text
    # 1. Redact Authorization: Bearer <token>
    sanitized = AUTH_HEADER_PATTERN.sub(r"\1[REDACTED]", text)
    # 2. Redact standalone Bearer <token>
    sanitized = BEARER_PATTERN.sub(r"\1[REDACTED]", sanitized)
    # 3. Redact common key-value secrets (api_key, secret, token, password)
    sanitized = KEY_VALUE_SECRET_PATTERN.sub(r"\1=[REDACTED]", sanitized)
    return sanitized


class PrivacyLogFilter(logging.Filter):
    """Logging filter that injects correlation ID and redacts credentials."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id.get()
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        return True


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured logging with privacy filter."""
    logger = logging.getLogger("rewind")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers on re-initialization
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [req:%(request_id)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(PrivacyLogFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique Request ID to each request and records execution duration."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # Check incoming header or generate new UUID4
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        token = current_request_id.set(req_id)

        start_time = time.perf_counter()
        try:
            logger.info("HTTP %s %s started", request.method, request.url.path)
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Request-ID"] = req_id

            try:
                telemetry.record_request()
                telemetry.record_latency("http_request", duration_ms)
                telemetry.record_outcome(f"http_{response.status_code}")
            except RuntimeError as telemetry_error:
                logger.warning("Request telemetry recording failed: %s", type(telemetry_error).__name__)

            logger.info(
                "HTTP %s %s completed status=%d duration=%.2fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            try:
                telemetry.record_request()
                telemetry.record_latency("http_request", duration_ms)
                telemetry.record_outcome("http_500")
            except RuntimeError as telemetry_error:
                logger.warning("Failed-request telemetry recording failed: %s", type(telemetry_error).__name__)
            logger.exception(
                "HTTP %s %s failed after %.2fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            current_request_id.reset(token)
