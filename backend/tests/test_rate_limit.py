"""Tests for the Redis-backed auth rate limiter.

Exercised without a live Redis: the limiter degrades to its in-process store,
which is the behaviour these tests pin down. The Redis path is covered by
injecting a fake client so the counter semantics (INCR + EXPIRE on first hit)
are asserted without a server.
"""

import pytest
from fastapi import HTTPException

from app.core.rate_limit import RateLimiter, _MemoryStore


class FakeRedis:
    """Minimal stand-in for the async Redis client the limiter uses."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.counters: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.expire_calls = 0

    async def incr(self, key: str) -> int:
        if self.fail:
            raise ConnectionError("redis down")
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expire_calls += 1
        self.expirations[key] = seconds

    async def delete(self, key: str) -> None:
        self.counters.pop(key, None)

    async def scan_iter(self, match: str):
        prefix = match.rstrip("*")
        for key in list(self.counters):
            if key.startswith(prefix):
                yield key


def _limiter_with(client, **kwargs) -> RateLimiter:
    """Build a limiter wired to a fake client, skipping real connection setup."""
    limiter = RateLimiter(namespace="test-ratelimit", **kwargs)
    limiter._client = client
    return limiter


class TestMemoryStore:
    def test_counts_within_window(self):
        store = _MemoryStore()
        assert [store.hit("k", 60) for _ in range(3)] == [1, 2, 3]

    def test_keys_are_independent(self):
        store = _MemoryStore()
        store.hit("a", 60)
        assert store.hit("b", 60) == 1

    def test_clear_single_key_leaves_others(self):
        store = _MemoryStore()
        store.hit("a", 60)
        store.hit("b", 60)
        store.clear("a")
        assert store.hit("a", 60) == 1
        assert store.hit("b", 60) == 2

    def test_clear_all(self):
        store = _MemoryStore()
        store.hit("a", 60)
        store.hit("b", 60)
        store.clear()
        assert store.hit("a", 60) == 1
        assert store.hit("b", 60) == 1

    def test_expired_hits_are_pruned(self):
        store = _MemoryStore()
        store.hit("k", 60)
        # A zero-length window makes every previous hit fall outside it.
        assert store.hit("k", 0) == 1


class TestRedisBackedLimiter:
    async def test_allows_up_to_max_attempts(self):
        limiter = _limiter_with(FakeRedis(), max_attempts=3, window_seconds=60)
        for _ in range(3):
            await limiter.check("k")

    async def test_blocks_beyond_max_attempts(self):
        limiter = _limiter_with(FakeRedis(), max_attempts=3, window_seconds=60)
        for _ in range(3):
            await limiter.check("k")
        with pytest.raises(HTTPException) as exc:
            await limiter.check("k")
        assert exc.value.status_code == 429
        assert exc.value.headers["Retry-After"] == "60"

    async def test_expire_set_once_so_the_window_does_not_slide(self):
        client = FakeRedis()
        limiter = _limiter_with(client, max_attempts=5, window_seconds=60)
        for _ in range(4):
            await limiter.check("k")
        # TTL is set when the counter starts, never refreshed afterwards —
        # otherwise a steady stream of attempts would keep the window open.
        assert client.expire_calls == 1
        assert client.expirations["test-ratelimit:k"] == 60

    async def test_distinct_keys_have_distinct_budgets(self):
        limiter = _limiter_with(FakeRedis(), max_attempts=1, window_seconds=60)
        await limiter.check("ip-a")
        await limiter.check("ip-b")
        with pytest.raises(HTTPException):
            await limiter.check("ip-a")

    async def test_reset_clears_a_single_key(self):
        limiter = _limiter_with(FakeRedis(), max_attempts=1, window_seconds=60)
        await limiter.check("k")
        await limiter.reset("k")
        await limiter.check("k")

    async def test_reset_without_key_clears_only_this_namespace(self):
        client = FakeRedis()
        client.counters["celery:job"] = 1
        limiter = _limiter_with(client, max_attempts=1, window_seconds=60)
        await limiter.check("k")
        await limiter.reset()
        # Redis is shared with Celery and the WhatsApp queue: a blanket flush
        # would take unrelated keys with it.
        assert "celery:job" in client.counters

    async def test_namespaced_keys_do_not_collide(self):
        client = FakeRedis()
        limiter = _limiter_with(client, max_attempts=5, window_seconds=60)
        await limiter.check("k")
        assert "test-ratelimit:k" in client.counters


class TestDegradedFallback:
    async def test_falls_back_to_memory_when_redis_fails(self):
        limiter = _limiter_with(FakeRedis(fail=True), max_attempts=2, window_seconds=60)
        await limiter.check("k")
        await limiter.check("k")
        with pytest.raises(HTTPException):
            await limiter.check("k")

    async def test_degrades_once_and_stops_retrying_redis(self):
        client = FakeRedis(fail=True)
        limiter = _limiter_with(client, max_attempts=5, window_seconds=60)
        await limiter.check("k")
        assert limiter._degraded is True
        client.fail = False
        await limiter.check("k")
        # Still on the in-process store: no further Redis calls are attempted.
        assert client.counters == {}

    async def test_no_client_available_still_enforces_the_limit(self):
        limiter = RateLimiter(max_attempts=1, window_seconds=60, namespace="test-ratelimit")
        limiter._degraded = True
        await limiter.check("k")
        with pytest.raises(HTTPException):
            await limiter.check("k")
