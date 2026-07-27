import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "visacanada-api"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_root_returns_welcome(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "VisaCanada" in data["message"]
