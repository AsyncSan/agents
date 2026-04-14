"""Secret Brokerage: manage consumer and provider secrets.

Secrets are stored encrypted in the database and injected into ephemeral
servers at runtime. Consumer secrets go to /workspace/secrets/consumer/,
provider secrets to /workspace/secrets/provider/. No key ever crosses
tenant boundaries. Destroyed with the server after execution.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider

router = APIRouter(prefix="/v1/me/secrets", tags=["secrets"])


class SecretsUpdateRequest(BaseModel):
    secrets: dict[str, str]  # {"OPENAI_API_KEY": "sk-...", "SERPER_API_KEY": "..."}


class SecretsListResponse(BaseModel):
    keys: list[str]  # only key names, never values


@router.put("", response_model=SecretsListResponse)
async def set_secrets(
    req: SecretsUpdateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set or update secrets. Merges with existing secrets."""
    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one_or_none()

    if not entity:
        raise APIError(404, ErrorCode.USER_NOT_FOUND, "User not found")

    existing = dict(entity.secrets or {})
    existing.update(req.secrets)
    entity.secrets = existing  # new dict triggers SQLAlchemy change detection
    await db.commit()

    return SecretsListResponse(keys=list(existing.keys()))


@router.get("", response_model=SecretsListResponse)
async def list_secrets(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List secret key names (never returns values)."""
    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one_or_none()

    if not entity:
        raise APIError(404, ErrorCode.USER_NOT_FOUND, "User not found")

    return SecretsListResponse(keys=list((entity.secrets or {}).keys()))


@router.delete("/{key_name}", status_code=204)
async def delete_secret(
    key_name: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a specific secret by key name."""
    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one_or_none()

    if not entity:
        raise APIError(404, ErrorCode.USER_NOT_FOUND, "User not found")

    existing = dict(entity.secrets or {})
    if key_name not in existing:
        raise APIError(404, ErrorCode.SECRET_NOT_FOUND, "Secret not found")

    del existing[key_name]
    entity.secrets = existing  # new dict triggers SQLAlchemy change detection
    await db.commit()
