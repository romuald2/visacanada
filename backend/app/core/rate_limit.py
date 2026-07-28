"""Lightweight in-process rate limiting for sensitive endpoints.

Provides brute-force / credential-stuffing protection on auth endpoints without
adding an external dependency. Uses a fixed-window counter keyed by client IP
(and optionally an identifier such as the login email).

Limitations: state is per-process and in-memory, so it does not coordinate
across multiple workers. For production behind several workers, back this with
the already-configured Redis (settings.redis_url). The public interface
(`RateLimiter.check`) stays the same, so swapping the store is transparent.
"""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Fixed-window rate limiter.

    Args:
        max_attempts: allowed attempts per window.
        window_seconds: window length in seconds.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]

    def check(self, key: str) -> None:
        """Record an attempt for `key`; raise 429 if the window is exceeded."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            if len(self._hits[key]) >= self.max_attempts:
                retry_after = int(self.window_seconds)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Trop de tentatives. Réessayez plus tard.",
                    headers={"Retry-After": str(retry_after)},
                )
            self._hits[key].append(now)

    def reset(self, key: str | None = None) -> None:
        """Clear counters (used on successful auth or in tests)."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


def client_ip(request: Request) -> str:
    """Best-effort client IP, honoring a single X-Forwarded-For hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Shared limiter for authentication endpoints: 5 attempts per minute per IP.
auth_limiter = RateLimiter(max_attempts=5, window_seconds=60)
