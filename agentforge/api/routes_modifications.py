"""Substantial modification tracking routes (Art. 43)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.modification import (
    CLASSIFICATIONS,
    MODIFICATION_TYPES,
    ModificationRecord,
)
from agentforge.modifications import modifications_to_markdown
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/modifications", tags=["modifications"])


class ModificationCreate(BaseModel):
    agent_id: str
    modification_type: str
    summary: str
    classification: str = "unclassified"
    rationale: str | None = None
    impact_assessment: dict[str, Any] | None = None
    version_from: int | None = None
    version_to: int | None = None
    triggered_reassessment: bool = False
    reassessment_at: datetime | None = None


class ModificationUpdate(BaseModel):
    classification: str | None = None
    summary: str | None = None
    rationale: str | None = None
    impact_assessment: dict[str, Any] | None = None
    triggered_reassessment: bool | None = None
    reassessment_at: datetime | None = None


class ModificationResponse(BaseModel):
    id: uuid.UUID
    agent_id: str
    version_from: int | None
    version_to: int | None
    modification_type: str
    classification: str
    summary: str
    rationale: str | None
    impact_assessment: dict[str, Any] | None
    triggered_reassessment: bool
    reassessment_at: datetime | None
    diff: dict[str, Any] | None
    created_by: str
    created_at: datetime
    updated_at: datetime


def _validate_type(t: str) -> None:
    if t not in MODIFICATION_TYPES:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"modification_type must be one of {list(MODIFICATION_TYPES)}",
        )


def _validate_classification(c: str) -> None:
    if c not in CLASSIFICATIONS:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"classification must be one of {list(CLASSIFICATIONS)}",
        )


async def _load_provider_agent(
    agent_id: str, user: dict, db: AsyncSession, write: bool = False
) -> Agent:
    """Load an agent and enforce ownership.

    Providers may only touch their own agents. Consumers may read
    modification logs for any agent (transparency for deployer due
    diligence under Art. 43), but must never create, patch, or delete
    records. Pass ``write=True`` for create/patch/delete routes to
    enforce that consumers cannot mutate.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    role = user.get("role")
    if write and role != "provider":
        raise APIError(
            403,
            ErrorCode.FORBIDDEN,
            "Only the agent provider may create, modify, or delete modification records.",
        )
    if role == "provider" and agent.provider_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your agent")
    return agent


def _to_response(r: ModificationRecord) -> ModificationResponse:
    return ModificationResponse(
        id=r.id,
        agent_id=r.agent_id,
        version_from=r.version_from,
        version_to=r.version_to,
        modification_type=r.modification_type,
        classification=r.classification,
        summary=r.summary,
        rationale=r.rationale,
        impact_assessment=r.impact_assessment,
        triggered_reassessment=r.triggered_reassessment,
        reassessment_at=r.reassessment_at,
        diff=r.diff,
        created_by=r.created_by,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("/types")
async def list_types():
    return {
        "modification_types": list(MODIFICATION_TYPES),
        "classifications": list(CLASSIFICATIONS),
    }


@router.get("", response_model=list[ModificationResponse])
async def list_modifications(
    agent_id: str = Query(..., description="Agent to list modifications for"),
    classification: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _load_provider_agent(agent_id, user, db)
    if classification is not None:
        _validate_classification(classification)

    stmt = select(ModificationRecord).where(ModificationRecord.agent_id == agent_id)
    if classification:
        stmt = stmt.where(ModificationRecord.classification == classification)
    stmt = stmt.order_by(ModificationRecord.created_at.desc())
    rows = list((await db.execute(stmt)).scalars().all())
    return [_to_response(r) for r in rows]


@router.post("", response_model=ModificationResponse, status_code=201)
async def create_modification(
    req: ModificationCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_type(req.modification_type)
    _validate_classification(req.classification)
    await _load_provider_agent(req.agent_id, user, db, write=True)

    record = ModificationRecord(
        agent_id=req.agent_id,
        version_from=req.version_from,
        version_to=req.version_to,
        modification_type=req.modification_type,
        classification=req.classification,
        summary=req.summary,
        rationale=req.rationale,
        impact_assessment=req.impact_assessment,
        triggered_reassessment=req.triggered_reassessment,
        reassessment_at=req.reassessment_at,
        created_by=str(user["id"]),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.patch("/{modification_id}", response_model=ModificationResponse)
async def update_modification(
    modification_id: uuid.UUID,
    req: ModificationUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModificationRecord).where(ModificationRecord.id == modification_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Modification not found")
    await _load_provider_agent(record.agent_id, user, db, write=True)

    if req.classification is not None:
        _validate_classification(req.classification)
        record.classification = req.classification
    if req.summary is not None:
        record.summary = req.summary
    if req.rationale is not None:
        record.rationale = req.rationale
    if req.impact_assessment is not None:
        record.impact_assessment = req.impact_assessment
    if req.triggered_reassessment is not None:
        record.triggered_reassessment = req.triggered_reassessment
    if req.reassessment_at is not None:
        record.reassessment_at = req.reassessment_at
    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.delete("/{modification_id}", status_code=204)
async def delete_modification(
    modification_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModificationRecord).where(ModificationRecord.id == modification_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Modification not found")
    await _load_provider_agent(record.agent_id, user, db, write=True)
    await db.delete(record)
    await db.commit()
    return None


async def _records_for_markdown(
    agent_id: str, db: AsyncSession
) -> list[dict[str, Any]]:
    stmt = (
        select(ModificationRecord)
        .where(ModificationRecord.agent_id == agent_id)
        .order_by(ModificationRecord.created_at.desc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "modification_type": r.modification_type,
            "classification": r.classification,
            "version_from": r.version_from,
            "version_to": r.version_to,
            "summary": r.summary,
            "rationale": r.rationale,
            "triggered_reassessment": r.triggered_reassessment,
            "reassessment_at": (
                r.reassessment_at.isoformat() if r.reassessment_at else None
            ),
        }
        for r in rows
    ]


@router.get("/export/markdown/{agent_id}", response_class=PlainTextResponse)
async def export_markdown(
    agent_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_provider_agent(agent_id, user, db)
    records = await _records_for_markdown(agent_id, db)
    md = modifications_to_markdown(agent.id, agent.name, records)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="modifications-{agent_id}.md"'
        },
    )


@router.get("/export/pdf/{agent_id}")
async def export_pdf(
    agent_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_provider_agent(agent_id, user, db)
    records = await _records_for_markdown(agent_id, db)
    md = modifications_to_markdown(agent.id, agent.name, records)
    pdf_bytes = markdown_to_pdf(
        md, title=f"Modification log · {agent.name}"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="modifications-{agent_id}.pdf"'
        },
    )


async def auto_log_version_bump(
    db: AsyncSession,
    *,
    agent_id: str,
    old_card: dict[str, Any],
    new_card: dict[str, Any],
    version_from: int,
    version_to: int,
    created_by: str,
) -> ModificationRecord:
    """Insert an auto-classified modification record on every agent PUT.

    Called from the agent update route; does not commit so the caller can
    bundle the write with the agent update. ``classify_auto`` sets the
    initial classification; the provider must review and confirm.
    """
    from agentforge.modifications import classify_auto, diff_cards, summarise_diff

    diff = diff_cards(old_card, new_card)
    suggested = classify_auto(diff)
    summary = summarise_diff(diff)

    record = ModificationRecord(
        agent_id=agent_id,
        version_from=version_from,
        version_to=version_to,
        modification_type="version_bump",
        classification=suggested,
        summary=summary,
        diff=diff or None,
        created_by=created_by,
    )
    db.add(record)
    return record
