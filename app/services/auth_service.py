import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_password_reset_token,
    hash_password,
    verify_password,
)
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.email_service import send_password_reset_email


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _ensure_aware(dt: datetime) -> datetime:
    """Return timezone-aware datetime, assuming UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, full_name: str, password: str) -> User:
        existing = await self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        await self._store_refresh_token(user.id, refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise ValueError("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        token_hash = _hash_token(refresh_token)
        db_token = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

        if not db_token or db_token.is_revoked:
            raise ValueError("Refresh token is revoked or not found")

        expires_at = _ensure_aware(db_token.expires_at)
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Refresh token has expired")

        # Rotate: revoke old, issue new
        db_token.is_revoked = True

        user_id = UUID(payload["sub"])
        new_access = create_access_token(str(user_id))
        new_refresh = create_refresh_token(str(user_id))
        await self._store_refresh_token(user_id, new_refresh)

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def logout(self, refresh_token: str) -> None:
        token_hash = _hash_token(refresh_token)
        db_token = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if db_token:
            db_token.is_revoked = True

    async def forgot_password(self, email: str) -> None:
        user = await self.db.scalar(select(User).where(User.email == email))
        if not user:
            return  # Silently succeed to prevent email enumeration

        token = generate_password_reset_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=2)

        # Fire background email (will fail silently if Celery not running)
        try:
            send_password_reset_email.delay(user.email, user.full_name, token)
        except Exception:
            pass

    async def reset_password(self, token: str, new_password: str) -> None:
        user = await self.db.scalar(
            select(User).where(User.password_reset_token == token)
        )
        if not user or not user.password_reset_expires:
            raise ValueError("Invalid or expired reset token")

        expires_at = _ensure_aware(user.password_reset_expires)
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Reset token has expired")

        user.hashed_password = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None

        # Revoke all existing refresh tokens
        tokens = await self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
        )
        for t in tokens.all():
            t.is_revoked = True

    async def _store_refresh_token(self, user_id: UUID, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        db_token = RefreshToken(
            user_id=user_id,
            token_hash=_hash_token(refresh_token),
            jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
        self.db.add(db_token)
        await self.db.flush()
