"""Human oversight assignment routes (Art. 14, 26(2), 4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.oversight import (
    AUTHORITY_LEVELS,
    OVERSIGHT_ROLES,
    OversightAssignment,
)
from agentforge.oversight import (
    build_agent_oversight_roster,
    roster_to_markdown,
    validate_authority,
    validate_role,
)
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/oversight", tags=["oversight"])


# ---------- Schemas ----------


class TrainingCertRef(BaseModel):
    certificate_id: str | None = None
    module_id: str | None = None
    module_title: str | None = None
    issued_at: datetime | None = None
    score_pct: int | None = None


class AssignmentCreate(BaseModel):
    staff_name: str = Field(..., min_length=1, max_length=255)
    staff_email: EmailStr
    staff_role_title: str | None = None
    oversight_role: str
    authority_level: str
    assigned_agent_ids: list[str] | None = None
    training_certificates: list[TrainingCertRef] | None = None
    competence_notes: str | None = None
    authority_source: str | None = None


class AssignmentUpdate(BaseModel):
    staff_name: str | None = None
    staff_email: EmailStr | None = None
    staff_role_title: str | None = None
    oversight_role: str | None = None
    authority_level: str | None = None
    assigned_agent_ids: list[str] | None = None
    training_certificates: list[TrainingCertRef] | None = None
    competence_notes: str | None = None
    authority_source: str | None = None
    active: bool | None = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    org_role: str
    staff_name: str
    staff_email: str
    staff_role_title: str | None
    oversight_role: str
    authority_level: str
    assigned_agent_ids: list[str] | None
    training_certificates: list[dict[str, Any]] | None
    competence_notes: str | None
    authority_source: str | None
    assigned_by: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


# ---------- Helpers ----------


def _require_org(user: dict) -> tuple[uuid.UUID, str]:
    role = user.get("role")
    if role not in {"consumer", "provider"}:
        raise APIError(
            403,
            ErrorCode.FORBIDDEN,
            "Only consumers and providers can manage oversight assignments",
        )
    return user["id"], role


async def _load_owned(
    assignment_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> OversightAssignment:
    result = await db.execute(
        select(OversightAssignment).where(
            OversightAssignment.id == assignment_id,
            OversightAssignment.org_id == org_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Assignment not found")
    return record


def _validate(req_role: str | None, req_auth: str | None) -> None:
    if req_role is not None:
        try:
            validate_role(req_role)
        except ValueError as exc:
            raise APIError(422, ErrorCode.INVALID_INPUT, str(exc)) from exc
    if req_auth is not None:
        try:
            validate_authority(req_auth)
        except ValueError as exc:
            raise APIError(422, ErrorCode.INVALID_INPUT, str(exc)) from exc


def _to_response(r: OversightAssignment) -> AssignmentResponse:
    return AssignmentResponse(
        id=r.id,
        org_id=r.org_id,
        org_role=r.org_role,
        staff_name=r.staff_name,
        staff_email=r.staff_email,
        staff_role_title=r.staff_role_title,
        oversight_role=r.oversight_role,
        authority_level=r.authority_level,
        assigned_agent_ids=r.assigned_agent_ids,
        training_certificates=r.training_certificates,
        competence_notes=r.competence_notes,
        authority_source=r.authority_source,
        assigned_by=r.assigned_by,
        active=r.active,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _assignment_as_dict(r: OversightAssignment) -> dict[str, Any]:
    return {
        "staff_name": r.staff_name,
        "staff_email": r.staff_email,
        "staff_role_title": r.staff_role_title,
        "oversight_role": r.oversight_role,
        "authority_level": r.authority_level,
        "assigned_agent_ids": r.assigned_agent_ids,
        "training_certificates": r.training_certificates or [],
        "competence_notes": r.competence_notes,
        "authority_source": r.authority_source,
        "assigned_by": r.assigned_by,
        "active": r.active,
    }


# ---------- Routes ----------


@router.get("/roles")
async def list_roles():
    return {
        "oversight_roles": list(OVERSIGHT_ROLES),
        "authority_levels": list(AUTHORITY_LEVELS),
    }


@router.get("/assignments", response_model=list[AssignmentResponse])
async def list_assignments(
    oversight_role: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    _validate(oversight_role, None)
    stmt = select(OversightAssignment).where(OversightAssignment.org_id == org_id)
    if oversight_role:
        stmt = stmt.where(OversightAssignment.oversight_role == oversight_role)
    if active_only:
        stmt = stmt.where(OversightAssignment.active.is_(True))
    stmt = stmt.order_by(OversightAssignment.created_at.desc())
    rows = list((await db.execute(stmt)).scalars().all())
    if agent_id:
        # Python-side filter: include org-wide (empty scope) or explicit match.
        rows = [
            r
            for r in rows
            if not r.assigned_agent_ids or agent_id in r.assigned_agent_ids
        ]
    return [_to_response(r) for r in rows]


@router.post("/assignments", response_model=AssignmentResponse, status_code=201)
async def create_assignment(
    req: AssignmentCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, org_role = _require_org(user)
    _validate(req.oversight_role, req.authority_level)

    certs = (
        [c.model_dump(exclude_none=True) for c in (req.training_certificates or [])]
        or None
    )

    record = OversightAssignment(
        org_id=org_id,
        org_role=org_role,
        staff_name=req.staff_name,
        staff_email=req.staff_email,
        staff_role_title=req.staff_role_title,
        oversight_role=req.oversight_role,
        authority_level=req.authority_level,
        assigned_agent_ids=req.assigned_agent_ids or None,
        training_certificates=certs,
        competence_notes=req.competence_notes,
        authority_source=req.authority_source,
        assigned_by=str(user["id"]),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    req: AssignmentUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    _validate(req.oversight_role, req.authority_level)
    record = await _load_owned(assignment_id, org_id, db)

    for attr in (
        "staff_name",
        "staff_email",
        "staff_role_title",
        "oversight_role",
        "authority_level",
        "competence_notes",
        "authority_source",
        "active",
    ):
        val = getattr(req, attr)
        if val is not None:
            setattr(record, attr, val)

    if req.assigned_agent_ids is not None:
        record.assigned_agent_ids = req.assigned_agent_ids or None
    if req.training_certificates is not None:
        record.training_certificates = (
            [c.model_dump(exclude_none=True) for c in req.training_certificates] or None
        )

    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    record = await _load_owned(assignment_id, org_id, db)
    await db.delete(record)
    await db.commit()
    return None


async def _load_org_assignments(
    org_id: uuid.UUID, db: AsyncSession
) -> list[OversightAssignment]:
    stmt = (
        select(OversightAssignment)
        .where(OversightAssignment.org_id == org_id)
        .where(OversightAssignment.active.is_(True))
    )
    return list((await db.execute(stmt)).scalars().all())


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


@router.get("/roster/{agent_id}")
async def get_roster(
    agent_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    agent = await _load_agent(agent_id, db)
    assignments = await _load_org_assignments(org_id, db)
    return build_agent_oversight_roster(
        agent.id,
        agent.name,
        agent.risk_class or "minimal",
        [_assignment_as_dict(r) for r in assignments],
    )


@router.get("/roster/{agent_id}/markdown", response_class=PlainTextResponse)
async def get_roster_markdown(
    agent_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    agent = await _load_agent(agent_id, db)
    assignments = await _load_org_assignments(org_id, db)
    roster = build_agent_oversight_roster(
        agent.id,
        agent.name,
        agent.risk_class or "minimal",
        [_assignment_as_dict(r) for r in assignments],
    )
    md = roster_to_markdown(roster)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="oversight-{agent_id}.md"'
        },
    )


@router.get("/roster/{agent_id}/pdf")
async def get_roster_pdf(
    agent_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    agent = await _load_agent(agent_id, db)
    assignments = await _load_org_assignments(org_id, db)
    roster = build_agent_oversight_roster(
        agent.id,
        agent.name,
        agent.risk_class or "minimal",
        [_assignment_as_dict(r) for r in assignments],
    )
    pdf_bytes = markdown_to_pdf(
        roster_to_markdown(roster),
        title=f"Oversight roster · {agent.name}",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="oversight-{agent_id}.pdf"'
        },
    )
