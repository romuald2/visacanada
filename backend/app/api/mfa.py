"""MFA (Multi-Factor Authentication) endpoints."""
import json
import secrets

import pyotp
import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, hash_password, verify_password
from app.core.database import get_db
from app.models.user import User, UserRole

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


class MFASetupResponse(BaseModel):
    secret: str
    qr_code_svg: str
    backup_codes: list[str]


class MFAVerifySetupRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MFAVerifyRequest(BaseModel):
    email: str
    password: str
    code: str = Field(min_length=6, max_length=8)  # TOTP=6, backup=8


class MFADisableRequest(BaseModel):
    password: str


def _generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes (8 digits each)."""
    return [f"{secrets.randbelow(100000000):08d}" for _ in range(count)]


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate TOTP secret and QR code for MFA setup.
    Only admin and consultant roles can enable MFA.
    """
    if current_user.role not in [UserRole.admin, UserRole.consultant]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA is only available for admin and consultant roles",
        )

    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled. Disable it first to reconfigure.",
        )

    # Generate TOTP secret
    secret = pyotp.random_base32()

    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="VisaCanada"
    )

    # Create SVG QR code
    img = qrcode.make(provisioning_uri, image_factory=qrcode.image.svg.SvgPathImage)
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer)
    qr_svg = buffer.getvalue().decode('utf-8')

    # Generate backup codes
    backup_codes = _generate_backup_codes()

    # Store secret temporarily (not enabled yet)
    current_user.totp_secret = secret
    current_user.backup_codes = json.dumps([hash_password(code) for code in backup_codes])
    await db.commit()

    return MFASetupResponse(
        secret=secret,
        qr_code_svg=qr_svg,
        backup_codes=backup_codes,
    )


@router.post("/verify-setup", status_code=status.HTTP_200_OK)
async def verify_setup(
    body: MFAVerifySetupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify TOTP code and enable MFA."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated. Call /auth/mfa/setup first.",
        )

    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled.",
        )

    # Verify code
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code. Please try again.",
        )

    # Enable MFA
    current_user.totp_enabled = True
    await db.commit()

    return {"message": "MFA enabled successfully"}


@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_mfa(
    body: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify MFA code during login.
    This endpoint is called after password verification.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this user",
        )

    # Try TOTP code
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(body.code, valid_window=1):
        return {"message": "MFA verification successful"}

    # Try backup codes
    if user.backup_codes:
        stored_codes = json.loads(user.backup_codes)
        for i, hashed_code in enumerate(stored_codes):
            if verify_password(body.code, hashed_code):
                # Remove used backup code
                stored_codes.pop(i)
                user.backup_codes = json.dumps(stored_codes)
                await db.commit()
                return {
                    "message": "MFA verification successful (backup code used)",
                    "remaining_backup_codes": len(stored_codes),
                }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid MFA code",
    )


@router.post("/disable", status_code=status.HTTP_200_OK)
async def disable_mfa(
    body: MFADisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disable MFA (requires password confirmation)."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    # Verify password
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # Disable MFA
    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None
    await db.commit()

    return {"message": "MFA disabled successfully"}


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
):
    """Get MFA status for current user."""
    backup_count = 0
    if current_user.backup_codes:
        backup_count = len(json.loads(current_user.backup_codes))

    return {
        "enabled": current_user.totp_enabled,
        "available": current_user.role in [UserRole.admin, UserRole.consultant],
        "backup_codes_remaining": backup_count if current_user.totp_enabled else None,
    }
