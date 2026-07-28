"""Compliance document workspace routes.

Persistent storage for FRIA drafts, Annex IV documents, and literacy
completions. Scoped per organisation (consumer or provider), with a
lightweight review workflow (draft → submitted → approved → archived).

Stale-detection: when a document references an agent whose current version
differs from the stored ``agent_version``, the list endpoint flags it so
downstream wizards can surface a re-review prompt.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.compliance_document import DOC_TYPES, STATUSES, ComplianceDocument

router = APIRouter(prefix="/v1/compliance/documents", tags=["compliance"])


# ---------- Schemas ----------


class ComplianceDocumentCreate(BaseModel):
    doc_type: str = Field(..., description=f"One of: {', '.join(DOC_TYPES)}")
    title: str
    payload: dict[str, Any]
    agent_id: str | None = None
    agent_version: int | None = None
    status: str = Field(default="draft")
    notes: str | None = None


class ComplianceDocumentUpdate(BaseModel):
    title: str | None = None
    payload: dict[str, Any] | None = None
    status: str | None = None
    notes: str | None = None
    agent_version: int | None = None


class ComplianceDocumentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    org_role: str
    doc_type: str
    title: str
    agent_id: str | None
    agent_version: int | None
    current_agent_version: int | None = None
    is_stale: bool = False
    status: str
    created_by: str
    approved_by: str | None
    approved_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ComplianceDocumentDetail(ComplianceDocumentResponse):
    payload: dict[str, Any]


class ComplianceListResponse(BaseModel):
    documents: list[ComplianceDocumentResponse]
    total: int
    stale_count: int


class ApproveRequest(BaseModel):
    notes: str | None = None


# ---------- Helpers ----------


def _validate_doc_type(doc_type: str) -> None:
    if doc_type not in DOC_TYPES:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"doc_type must be one of {list(DOC_TYPES)}",
        )


def _validate_status(status: str) -> None:
    if status not in STATUSES:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"status must be one of {list(STATUSES)}",
        )


def _require_org(user: dict) -> tuple[uuid.UUID, str]:
    role = user.get("role")
    if role not in {"consumer", "provider"}:
        raise APIError(403, ErrorCode.FORBIDDEN, "Only consumers and providers can own compliance documents")
    return user["id"], role


async def _load_owned(
    doc_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> ComplianceDocument:
    result = await db.execute(
        select(ComplianceDocument).where(
            ComplianceDocument.id == doc_id,
            ComplianceDocument.org_id == org_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Document not found")
    return doc


async def _current_agent_version(agent_id: str | None, db: AsyncSession) -> int | None:
    if not agent_id:
        return None
    result = await db.execute(select(Agent.version).where(Agent.id == agent_id))
    value = result.scalar_one_or_none()
    return int(value) if value is not None else None


def _to_response(
    doc: ComplianceDocument,
    current_agent_version: int | None,
) -> ComplianceDocumentResponse:
    is_stale = bool(
        doc.agent_id
        and doc.agent_version is not None
        and current_agent_version is not None
        and current_agent_version != doc.agent_version
    )
    return ComplianceDocumentResponse(
        id=doc.id,
        org_id=doc.org_id,
        org_role=doc.org_role,
        doc_type=doc.doc_type,
        title=doc.title,
        agent_id=doc.agent_id,
        agent_version=doc.agent_version,
        current_agent_version=current_agent_version,
        is_stale=is_stale,
        status=doc.status,
        created_by=doc.created_by,
        approved_by=doc.approved_by,
        approved_at=doc.approved_at,
        notes=doc.notes,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _to_detail(
    doc: ComplianceDocument,
    current_agent_version: int | None,
) -> ComplianceDocumentDetail:
    base = _to_response(doc, current_agent_version)
    return ComplianceDocumentDetail(**base.model_dump(), payload=doc.payload)


# ---------- Routes ----------


@router.get("", response_model=ComplianceListResponse)
async def list_documents(
    doc_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List compliance documents owned by the authenticated organisation."""
    org_id, _ = _require_org(user)
    if doc_type is not None:
        _validate_doc_type(doc_type)
    if status is not None:
        _validate_status(status)

    stmt = select(ComplianceDocument).where(ComplianceDocument.org_id == org_id)
    if doc_type:
        stmt = stmt.where(ComplianceDocument.doc_type == doc_type)
    if status:
        stmt = stmt.where(ComplianceDocument.status == status)
    if agent_id:
        stmt = stmt.where(ComplianceDocument.agent_id == agent_id)
    stmt = stmt.order_by(ComplianceDocument.updated_at.desc())

    docs = list((await db.execute(stmt)).scalars().all())

    agent_ids = {d.agent_id for d in docs if d.agent_id}
    current_versions: dict[str, int] = {}
    if agent_ids:
        version_rows = (
            await db.execute(
                select(Agent.id, Agent.version).where(Agent.id.in_(agent_ids))
            )
        ).all()
        current_versions = {aid: int(v) for aid, v in version_rows}

    responses = [
        _to_response(d, current_versions.get(d.agent_id) if d.agent_id else None)
        for d in docs
    ]
    stale_count = sum(1 for r in responses if r.is_stale)
    return ComplianceListResponse(
        documents=responses,
        total=len(responses),
        stale_count=stale_count,
    )


@router.get("/summary")
async def documents_summary(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Counts per doc_type and per status for the authenticated organisation."""
    org_id, _ = _require_org(user)

    by_type_rows = (
        await db.execute(
            select(ComplianceDocument.doc_type, func.count())
            .where(ComplianceDocument.org_id == org_id)
            .group_by(ComplianceDocument.doc_type)
        )
    ).all()
    by_status_rows = (
        await db.execute(
            select(ComplianceDocument.status, func.count())
            .where(ComplianceDocument.org_id == org_id)
            .group_by(ComplianceDocument.status)
        )
    ).all()

    return {
        "by_doc_type": {row[0]: int(row[1]) for row in by_type_rows},
        "by_status": {row[0]: int(row[1]) for row in by_status_rows},
    }


@router.post("", response_model=ComplianceDocumentDetail, status_code=201)
async def create_document(
    req: ComplianceDocumentCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a new compliance document for the authenticated organisation."""
    org_id, org_role = _require_org(user)
    _validate_doc_type(req.doc_type)
    _validate_status(req.status)

    doc = ComplianceDocument(
        org_id=org_id,
        org_role=org_role,
        doc_type=req.doc_type,
        title=req.title,
        agent_id=req.agent_id,
        agent_version=req.agent_version,
        payload=req.payload,
        status=req.status,
        created_by=str(user["id"]),
        notes=req.notes,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    current = await _current_agent_version(doc.agent_id, db)
    return _to_detail(doc, current)


@router.get("/{doc_id}", response_model=ComplianceDocumentDetail)
async def get_document(
    doc_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    doc = await _load_owned(doc_id, org_id, db)
    current = await _current_agent_version(doc.agent_id, db)
    return _to_detail(doc, current)


@router.patch("/{doc_id}", response_model=ComplianceDocumentDetail)
async def update_document(
    doc_id: uuid.UUID,
    req: ComplianceDocumentUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    doc = await _load_owned(doc_id, org_id, db)

    if req.status is not None:
        _validate_status(req.status)
        doc.status = req.status
        if req.status != "approved":
            doc.approved_by = None
            doc.approved_at = None
    if req.title is not None:
        doc.title = req.title
    if req.payload is not None:
        doc.payload = req.payload
    if req.notes is not None:
        doc.notes = req.notes
    if req.agent_version is not None:
        doc.agent_version = req.agent_version

    await db.commit()
    await db.refresh(doc)
    current = await _current_agent_version(doc.agent_id, db)
    return _to_detail(doc, current)


@router.post("/{doc_id}/approve", response_model=ComplianceDocumentDetail)
async def approve_document(
    doc_id: uuid.UUID,
    req: ApproveRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    doc = await _load_owned(doc_id, org_id, db)
    if doc.status == "archived":
        raise APIError(409, ErrorCode.INVALID_INPUT, "Archived documents cannot be approved")
    doc.status = "approved"
    doc.approved_by = str(user["id"])
    doc.approved_at = datetime.now(timezone.utc)
    if req.notes is not None:
        doc.notes = req.notes
    await db.commit()
    await db.refresh(doc)
    current = await _current_agent_version(doc.agent_id, db)
    return _to_detail(doc, current)


@router.post("/{doc_id}/archive", response_model=ComplianceDocumentDetail)
async def archive_document(
    doc_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    doc = await _load_owned(doc_id, org_id, db)
    doc.status = "archived"
    await db.commit()
    await db.refresh(doc)
    current = await _current_agent_version(doc.agent_id, db)
    return _to_detail(doc, current)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    doc = await _load_owned(doc_id, org_id, db)
    await db.delete(doc)
    await db.commit()
    return None
