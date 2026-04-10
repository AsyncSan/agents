"""Authentication: API key generation, validation, and JWT tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.config import settings
from agentforge.db import get_db
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider

api_key_header = APIKeyHeader(name="X-API-Key")


def generate_api_key() -> str:
    return f"af_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(f"{settings.api_key_salt}{key}".encode()).hexdigest()


def create_jwt(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate API key and return user info with role."""
    key_hash = hash_api_key(api_key)

    # Check providers
    result = await db.execute(
        select(Provider).where(Provider.api_key_hash == key_hash)
    )
    provider = result.scalar_one_or_none()
    if provider:
        return {"id": provider.id, "role": "provider", "name": provider.name}

    # Check consumers
    result = await db.execute(
        select(Consumer).where(Consumer.api_key_hash == key_hash)
    )
    consumer = result.scalar_one_or_none()
    if consumer:
        return {"id": consumer.id, "role": "consumer", "name": consumer.name}

    raise HTTPException(status_code=401, detail="Invalid API key")


def require_role(role: str):
    """Dependency that checks the user has a specific role."""
    async def check(user: dict = Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(status_code=403, detail=f"Requires {role} role")
        return user
    return check
