"""Rate limiting for sensitive endpoints, backed by Redis.

Provides brute-force / credential-stuffing protection on auth endpoints using a
fixed-window counter keyed by client IP (and optionally an identifier such as
the login email).

Counters live in Redis (settings.redis_url) so that every worker sees the same
window: an in-process counter lets an attacker multiply their allowance by the
number of workers. When Redis is unreachable the limiter falls back to a
per-process counter rather than failing open entirely — degraded protection,
but a Redis outage never takes authentication down with it.
"""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.config import settings

try:  # pragma: no cover - exercised by the absence of the extra, not by tests
    from redis import asyncio as aioredis
except ImportError:  # redis is a declared dependency; guard kept for safety
    aioredis = None


class _MemoryStore:
    """Per-process fixed-window counter, used as the degraded fallback."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def hit(self, key: str, window_seconds: int) -> int:
        """Record an attempt and return the count within the current window."""
        now = time.monotonic()
        with self._lock:
            cutoff = now - window_seconds
            kept = [t for t in self._hits[key] if t > cutoff]
            kept.append(now)
            self._hits[key] = kept
            return len(kept)

    def clear(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


class RateLimiter:
    """Fixed-window rate limiter shared across workers via Redis.

    Args:
        max_attempts: allowed attempts per window.
        window_seconds: window length in seconds.
        namespace: Redis key prefix, so distinct limiters cannot collide.
    """

    REDIS_TIMEOUT_SECONDS = 0.5

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 60,
        namespace: str = "ratelimit",
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.namespace = namespace
        self._memory = _MemoryStore()
        self._client = None
        self._degraded = False

    def _redis_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def _get_client(self):
        """Lazily connect to Redis; return None once the store is unusable.

        The client is created on first use rather than at import time so that
        the module stays importable (and testable) without a live Redis.
        """
        if self._degraded or aioredis is None:
            return None
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    # Short budget on purpose: this sits on the login path, so a
                    # slow or absent Redis must degrade fast rather than add
                    # seconds of latency to every authentication attempt.
                    socket_connect_timeout=self.REDIS_TIMEOUT_SECONDS,
                    socket_timeout=self.REDIS_TIMEOUT_SECONDS,
                )
            except Exception:
                self._degraded = True
                return None
        return self._client

    async def _hit(self, key: str) -> int:
        """Increment the window counter for `key` and return its new value."""
        client = await self._get_client()
        if client is not None:
            try:
                redis_key = self._redis_key(key)
                # INCR then EXPIRE on first hit: the TTL is what makes the
                # window slide forward, so it is only set when the counter
                # starts, never refreshed on subsequent attempts.
                count = await client.incr(redis_key)
                if count == 1:
                    await client.expire(redis_key, self.window_seconds)
                return count
            except Exception:
                # Redis went away mid-flight. Degrade for the rest of this
                # process instead of retrying on every single request.
                self._degraded = True
        return self._memory.hit(key, self.window_seconds)

    async def check(self, key: str) -> None:
        """Record an attempt for `key`; raise 429 if the window is exceeded."""
        if await self._hit(key) > self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez plus tard.",
                headers={"Retry-After": str(int(self.window_seconds))},
            )

    async def reset(self, key: str | None = None) -> None:
        """Clear counters (used on successful auth or in tests)."""
        self._memory.clear(key)
        client = await self._get_client()
        if client is None:
            return
        try:
            if key is None:
                # Only this limiter's namespace, never a blanket FLUSHDB: the
                # same Redis instance also backs Celery and the WhatsApp queue.
                async for found in client.scan_iter(match=f"{self.namespace}:*"):
                    await client.delete(found)
            else:
                await client.delete(self._redis_key(key))
        except Exception:
            self._degraded = True


def client_ip(request: Request) -> str:
    """Best-effort client IP, honoring a single X-Forwarded-For hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Shared limiter for authentication endpoints: 5 attempts per minute per IP.
auth_limiter = RateLimiter(max_attempts=5, window_seconds=60, namespace="auth-ratelimit")
