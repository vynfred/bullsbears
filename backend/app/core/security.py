# backend/app/core/security.py
"""
Admin JWT authentication for protected endpoints.
Uses HS256 with secret from ADMIN_JWT_SECRET env var.
"""

from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

# OAuth2 scheme for swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/auth/login", auto_error=False)

ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=30)) -> str:
    """Create a JWT token with expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.ADMIN_JWT_SECRET, algorithm=ALGORITHM)


async def verify_admin_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Verify JWT token and return payload.
    Use as: dependencies=[Depends(verify_admin_token)]
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    if not settings.ADMIN_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_JWT_SECRET not configured"
        )

    try:
        payload = jwt.decode(token, settings.ADMIN_JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def verify_admin_credentials(email: str, password: str) -> bool:
    """Verify admin email and password against env vars."""
    admin_pwd = settings.admin_password  # Uses property that checks both env vars
    if not settings.ADMIN_EMAIL or not admin_pwd:
        return False
    return email == settings.ADMIN_EMAIL and password == admin_pwd
