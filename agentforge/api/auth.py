"""Authentication: API key generation, validation, and JWT tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from jose import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.errors import APIError, ErrorCode
from agentforge.config import settings
from agentforge.db import get_db
from agentforge.models.api_key import APIKey
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider

api_key_header = APIKeyHeader(name="X-API-Key")

# Scope hierarchy: read < execute < admin
SCOPE_LEVELS = {"read": 0, "execute": 1, "admin": 2}


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
    """Validate API key and return user info with role and scope."""
    key_hash = hash_api_key(api_key)

    # Check scoped API keys first
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.revoked.is_(False))
    )
    scoped_key = result.scalar_one_or_none()
    if scoped_key:
        # Update last_used_at (fire and forget)
        await db.execute(
            update(APIKey)
            .where(APIKey.id == scoped_key.id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return {
            "id": scoped_key.owner_id,
            "role": scoped_key.owner_role,
            "name": scoped_key.name,
            "scope": scoped_key.scope,
            "api_key_id": str(scoped_key.id),
        }

    # Fallback: legacy provider keys (scope = admin)
    result = await db.execute(
        select(Provider).where(Provider.api_key_hash == key_hash)
    )
    provider = result.scalar_one_or_none()
    if provider:
        return {"id": provider.id, "role": "provider", "name": provider.name, "scope": "admin"}

    # Fallback: legacy consumer keys (scope = admin)
    result = await db.execute(
        select(Consumer).where(Consumer.api_key_hash == key_hash)
    )
    consumer = result.scalar_one_or_none()
    if consumer:
        return {"id": consumer.id, "role": "consumer", "name": consumer.name, "scope": "admin"}

    raise APIError(401, ErrorCode.INVALID_API_KEY, "Invalid API key")


def require_role(role: str | None = None):
    """Dependency that checks the user has a specific role. None = any role."""
    async def check(user: dict = Depends(get_current_user)):
        if role and user["role"] != role:
            raise APIError(403, ErrorCode.ROLE_REQUIRED, f"Requires {role} role")
        return user
    return check


def require_scope(min_scope: str):
    """Dependency that checks the API key has at least the required scope level.

    Scope hierarchy: read < execute < admin.
    Legacy keys (no explicit scope) default to admin.
    """
    async def check(user: dict = Depends(get_current_user)):
        user_scope = user.get("scope", "admin")
        required_level = SCOPE_LEVELS.get(min_scope, 2)
        current_level = SCOPE_LEVELS.get(user_scope, 2)
        if current_level < required_level:
            raise APIError(
                403, ErrorCode.FORBIDDEN,
                f"This action requires '{min_scope}' scope, your key has '{user_scope}'",
            )
        return user
    return check
