"""Auditor read-only share management (owner-facing)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.audit_shares import (
    DEFAULT_TTL_DAYS,
    MAX_TTL_DAYS,
    generate_token,
    is_active,
    resolve_expiry,
)
from agentforge.db import get_db
from agentforge.models.audit_share import AuditShare

router = APIRouter(prefix="/v1/audit-shares", tags=["audit-shares"])


class AuditShareCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    scope_agent_id: str | None = None
    auditor_name: str | None = None
    auditor_organisation: str | None = None
    auditor_email: EmailStr | None = None
    notes: str | None = None
    ttl_days: int | None = Field(
        default=None, ge=1, le=MAX_TTL_DAYS, description=f"1..{MAX_TTL_DAYS}"
    )


class AuditShareResponse(BaseModel):
    id: uuid.UUID
    label: str
    token_prefix: str
    scope_agent_id: str | None
    auditor_name: str | None
    auditor_organisation: str | None
    auditor_email: str | None
    notes: str | None
    expires_at: datetime
    revoked_at: datetime | None
    active: bool
    access_count: int
    last_accessed_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class AuditShareCreateResponse(AuditShareResponse):
    token: str
    url: str


def _require_org(user: dict) -> tuple[uuid.UUID, str]:
    role = user.get("role")
    if role not in {"consumer", "provider"}:
        raise APIError(
            403,
            ErrorCode.FORBIDDEN,
            "Only consumers and providers can manage audit shares",
        )
    return user["id"], role


def _to_response(s: AuditShare) -> AuditShareResponse:
    return AuditShareResponse(
        id=s.id,
        label=s.label,
        token_prefix=s.token_prefix,
        scope_agent_id=s.scope_agent_id,
        auditor_name=s.auditor_name,
        auditor_organisation=s.auditor_organisation,
        auditor_email=s.auditor_email,
        notes=s.notes,
        expires_at=s.expires_at,
        revoked_at=s.revoked_at,
        active=is_active(s.expires_at, s.revoked_at),
        access_count=s.access_count,
        last_accessed_at=s.last_accessed_at,
        created_by=s.created_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("", response_model=list[AuditShareResponse])
async def list_shares(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    stmt = (
        select(AuditShare)
        .where(AuditShare.org_id == org_id)
        .order_by(AuditShare.created_at.desc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [_to_response(r) for r in rows]


@router.post("", response_model=AuditShareCreateResponse, status_code=201)
async def create_share(
    req: AuditShareCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, org_role = _require_org(user)
    try:
        expires = resolve_expiry(req.ttl_days or DEFAULT_TTL_DAYS)
    except ValueError as exc:
        raise APIError(422, ErrorCode.INVALID_INPUT, str(exc)) from exc

    raw, token_hash, prefix = generate_token()
    share = AuditShare(
        org_id=org_id,
        org_role=org_role,
        label=req.label,
        token_hash=token_hash,
        token_prefix=prefix,
        scope_agent_id=req.scope_agent_id,
        auditor_name=req.auditor_name,
        auditor_organisation=req.auditor_organisation,
        auditor_email=req.auditor_email,
        notes=req.notes,
        expires_at=expires,
        created_by=str(user["id"]),
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    base = _to_response(share)
    return AuditShareCreateResponse(
        **base.model_dump(),
        token=raw,
        url=f"/audit/{raw}",
    )


@router.post("/{share_id}/revoke", response_model=AuditShareResponse)
async def revoke_share(
    share_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    share = (
        await db.execute(
            select(AuditShare).where(
                AuditShare.id == share_id, AuditShare.org_id == org_id
            )
        )
    ).scalar_one_or_none()
    if share is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Share not found")
    if share.revoked_at is None:
        share.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(share)
    return _to_response(share)


@router.delete("/{share_id}", status_code=204)
async def delete_share(
    share_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    share = (
        await db.execute(
            select(AuditShare).where(
                AuditShare.id == share_id, AuditShare.org_id == org_id
            )
        )
    ).scalar_one_or_none()
    if share is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Share not found")
    await db.delete(share)
    await db.commit()
    return None
