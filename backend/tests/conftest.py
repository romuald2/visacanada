"""Shared pytest fixtures for the backend test suite."""

import pytest

from app.core.rate_limit import auth_limiter


@pytest.fixture(autouse=True)
async def _reset_rate_limiter():
    """Clear the auth rate limiter around every test.

    The limiter is a process-wide singleton, so counters would otherwise
    accumulate across tests and trip spurious 429 responses. Production
    behaviour is unaffected — this only resets state between tests.

    Tests run without a live Redis, so the limiter degrades to its in-process
    store on first use and `reset()` clears that store.
    """
    await auth_limiter.reset()
    yield
    await auth_limiter.reset()
