"""Tests for MFA (Multi-Factor Authentication) endpoints."""
import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import hash_password
from app.core.database import get_db
from app.main import app
from app.models.user import Base, User, UserRole

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
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def create_user(db_session):
    """Factory to create users."""
    async def _create(email: str, password: str, role: UserRole):
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test User",
            role=role,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    return _create


@pytest.fixture
def get_token():
    """Generate JWT token for testing."""
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.core.config import settings

    def _get_token(user_id: int, email: str, role: UserRole):
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role.value,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access",
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return _get_token


@pytest.fixture
async def admin_token(create_user, get_token):
    """Create admin user and return token."""
    user = await create_user("admin@test.com", "password123", UserRole.admin)
    return get_token(user.id, user.email, user.role)


@pytest.mark.asyncio
async def test_mfa_setup_success(client: AsyncClient, admin_token: str):
    """Admin can setup MFA."""
    response = await client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "qr_code_svg" in data
    assert "backup_codes" in data
    assert len(data["backup_codes"]) == 8
    assert all(len(code) == 8 for code in data["backup_codes"])


@pytest.mark.asyncio
async def test_mfa_setup_consultant_allowed(client: AsyncClient, create_user, get_token):
    """Consultant can setup MFA."""
    user = await create_user("consultant@test.com", "pass123", UserRole.consultant)
    token = get_token(user.id, user.email, user.role)

    response = await client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mfa_setup_candidat_forbidden(client: AsyncClient, create_user, get_token):
    """Candidat cannot setup MFA."""
    user = await create_user("candidat@test.com", "pass123", UserRole.candidat)
    token = get_token(user.id, user.email, user.role)

    response = await client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mfa_verify_setup_success(client: AsyncClient, admin_token: str, db_session):
    """Verify TOTP code and enable MFA."""
    # Setup MFA
    response = await client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    secret = response.json()["secret"]

    # Generate valid TOTP code
    import pyotp
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Verify setup
    response = await client.post(
        "/auth/mfa/verify-setup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"code": code},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "MFA enabled successfully"


@pytest.mark.asyncio
async def test_mfa_verify_setup_invalid_code(client: AsyncClient, admin_token: str):
    """Invalid TOTP code fails verification."""
    # Setup MFA
    await client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Try invalid code
    response = await client.post(
        "/auth/mfa/verify-setup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"code": "000000"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_mfa_login_flow(client: AsyncClient, create_user, db_session):
    """Complete MFA login flow."""
    import pyotp

    # Create admin user
    user = await create_user("mfa@test.com", "password123", UserRole.admin)

    # Setup MFA manually
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled = True
    await db_session.commit()

    # Generate valid code
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Verify MFA
    response = await client.post(
        "/auth/mfa/verify",
        json={
            "email": "mfa@test.com",
            "password": "password123",
            "code": code,
        },
    )
    assert response.status_code == 200
    assert "verification successful" in response.json()["message"]


@pytest.mark.asyncio
async def test_mfa_backup_code_login(client: AsyncClient, create_user, db_session):
    """Backup codes work for login."""
    import pyotp

    from app.api.auth import hash_password

    # Create admin user
    user = await create_user("mfa-backup@test.com", "password123", UserRole.admin)

    # Setup MFA with backup codes (8 digits as generated)
    secret = pyotp.random_base32()
    backup_code = "12345678"
    user.totp_secret = secret
    user.totp_enabled = True
    user.backup_codes = json.dumps([hash_password(backup_code)])
    await db_session.commit()

    # Use backup code (pad to 8 digits or adjust validation)
    response = await client.post(
        "/auth/mfa/verify",
        json={
            "email": "mfa-backup@test.com",
            "password": "password123",
            "code": backup_code,  # 8 digits
        },
    )
    assert response.status_code == 200
    assert "backup code used" in response.json()["message"]
    assert response.json()["remaining_backup_codes"] == 0


@pytest.mark.asyncio
async def test_mfa_disable(client: AsyncClient, create_user, get_token, db_session):
    """Disable MFA with password confirmation."""
    import pyotp

    # Create admin with MFA enabled
    user = await create_user("mfa-disable@test.com", "password123", UserRole.admin)
    user.totp_secret = pyotp.random_base32()
    user.totp_enabled = True
    await db_session.commit()

    token = get_token(user.id, user.email, user.role)

    # Disable MFA
    response = await client.post(
        "/auth/mfa/disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "password123"},
    )
    assert response.status_code == 200

    # Verify MFA is disabled
    response = await client.get(
        "/auth/mfa/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_mfa_status(client: AsyncClient, admin_token: str):
    """Get MFA status."""
    response = await client.get(
        "/auth/mfa/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "available" in data
    assert data["available"] is True


@pytest.mark.asyncio
async def test_mfa_setup_already_enabled(client: AsyncClient, create_user, get_token, db_session):
    """Cannot setup MFA if already enabled."""
    import pyotp

    user = await create_user("mfa-already@test.com", "pass123", UserRole.admin)
    user.totp_secret = pyotp.random_base32()
    user.totp_enabled = True
    await db_session.commit()

    token = get_token(user.id, user.email, user.role)

    response = await client.post(
        "/auth/mfa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "already enabled" in response.json()["detail"]
