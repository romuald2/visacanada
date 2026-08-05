import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.user import Base

# Use SQLite for tests (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def registered_user(client: AsyncClient):
    """Register a user and return the response data."""
    user_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User",
        "role": "candidat",
    }
    response = await client.post("/auth/register", json=user_data)
    return response.json()


@pytest.fixture
async def auth_token(client: AsyncClient, registered_user):
    """Login and return the access token."""
    login_data = {"email": "test@example.com", "password": "securepassword123"}
    response = await client.post("/auth/login", json=login_data)
    return response.json()["access_token"]


# --- Registration Tests ---


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    user_data = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "full_name": "New User",
        "role": "candidat",
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "candidat"
    assert data["is_active"] is True
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, registered_user):
    user_data = {
        "email": "test@example.com",
        "password": "anotherpassword123",
        "full_name": "Another User",
        "role": "candidat",
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    user_data = {
        "email": "not-an-email",
        "password": "securepassword123",
        "full_name": "Bad Email User",
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    user_data = {
        "email": "short@example.com",
        "password": "short",
        "full_name": "Short Pass",
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 422


# --- Login Tests ---


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, registered_user):
    login_data = {"email": "test@example.com", "password": "securepassword123"}
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, registered_user):
    login_data = {"email": "test@example.com", "password": "wrongpassword"}
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    login_data = {"email": "noone@example.com", "password": "securepassword123"}
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 401


# --- /me Tests ---


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    response = await client.get("/auth/me")
    # HTTPBearer answers 401 when the Authorization header is absent, which is
    # what RFC 9110 prescribes for missing credentials (403 is for credentials
    # that are present but insufficient).
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    headers = {"Authorization": "Bearer invalidtoken123"}
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 401


# --- Refresh Token Tests ---


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, registered_user):
    # Login first
    login_data = {"email": "test@example.com", "password": "securepassword123"}
    login_response = await client.post("/auth/login", json=login_data)
    refresh_token = login_response.json()["refresh_token"]

    # Refresh
    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post("/auth/refresh", json={"refresh_token": "invalidtoken"})
    assert response.status_code == 401
