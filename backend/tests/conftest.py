"""Shared pytest fixtures for the backend test suite."""

import pytest

from app.core.rate_limit import auth_limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the in-memory auth rate limiter around every test.

    The limiter is a process-wide singleton, so counters would otherwise
    accumulate across tests and trip spurious 429 responses. Production
    behaviour is unaffected — this only resets state between tests.
    """
    auth_limiter.reset()
    yield
    auth_limiter.reset()
