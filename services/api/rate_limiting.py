"""In-memory sliding window rate limiter for Rewind API endpoints.

Implements:
- OPS-003: Rate limits, resource bounds, and concurrency protection
- BE-SAFE-007: Apply documented request limits and rate limiting
- NFR-SCALE-001: Graceful degradation under load
"""

from collections import defaultdict
import threading
import time
from typing import Callable
from fastapi import Request

from services.api.config import settings
from services.api.errors import AppException


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """Check if request is permitted under sliding window.

        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Filter timestamps within active window
            history = [ts for ts in self._requests[key] if ts > cutoff]

            if len(history) >= max_requests:
                # Calculate remaining time until oldest request in window expires
                oldest_in_window = history[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now))
                self._requests[key] = history
                return False, retry_after

            history.append(now)
            self._requests[key] = history
            return True, 0

    def reset(self) -> None:
        """Reset all rate limiter tracking state (useful for test suites)."""
        with self._lock:
            self._requests.clear()


# Global limiter singleton
limiter = SlidingWindowRateLimiter()


class RateLimiter:
    """FastAPI Dependency for route-level rate limiting."""

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: int = 60,
        key_func: Callable[[Request], str] | None = None,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func

    async def __call__(self, request: Request) -> None:
        effective_max = self.max_requests or settings.rate_limit_per_minute

        if self.key_func:
            key = self.key_func(request)
        else:
            # Prioritize authenticated viewer user_id header, falling back to client IP
            user_id = request.headers.get("x-user-id")
            client_ip = request.client.host if request.client else "127.0.0.1"
            key = f"user:{user_id}" if user_id else f"ip:{client_ip}"

        route_key = f"{request.url.path}:{key}"
        allowed, retry_after = limiter.is_allowed(
            key=route_key,
            max_requests=effective_max,
            window_seconds=self.window_seconds,
        )

        if not allowed:
            raise AppException(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded. Maximum {effective_max} requests per {self.window_seconds}s.",
                details={"retry_after_seconds": retry_after},
            )
