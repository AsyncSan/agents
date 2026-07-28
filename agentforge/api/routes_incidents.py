"""Incident reporting routes (Art. 73)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.incidents import (
    SEVERITY_DEADLINE_DAYS,
    build_incident_report_template,
    deadline_for,
    incident_report_to_markdown,
    severity_catalog,
    time_remaining,
)
from agentforge.models.agent import Agent
from agentforge.models.incident import SEVERITIES, STATUSES, IncidentReport
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/incidents", tags=["incidents"])


# ---------- Schemas ----------


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: str = Field(..., min_length=1)
    severity: str
    detected_at: datetime
    awareness_at: datetime | None = None
    agent_id: str | None = None
    agent_version: int | None = None
    task_id: str | None = None
    affected_persons_estimate: int | None = None
    root_cause: str | None = None
    mitigation_taken: str | None = None
    mitigation_planned: str | None = None
    extra: dict[str, Any] | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    severity: str | None = None
    status: str | None = None
    detected_at: datetime | None = None
    awareness_at: datetime | None = None
    affected_persons_estimate: int | None = None
    root_cause: str | None = None
    mitigation_taken: str | None = None
    mitigation_planned: str | None = None
    extra: dict[str, Any] | None = None


class ReportedRequest(BaseModel):
    authority_name: str | None = None
    authority_reference: str | None = None
    reported_at: datetime | None = None


class IncidentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: str | None
    agent_version: int | None
    task_id: str | None
    title: str
    summary: str
    severity: str
    status: str
    detected_at: datetime
    awareness_at: datetime
    affected_persons_estimate: int | None
    root_cause: str | None
    mitigation_taken: str | None
    mitigation_planned: str | None
    reported_to_authority_at: datetime | None
    authority_name: str | None
    authority_reference: str | None
    # Derived
    deadline_at: datetime
    deadline_days: int
    time_remaining_seconds: int
    overdue: bool
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]
    total: int
    overdue_count: int
    open_count: int


class ProviderContactRequest(BaseModel):
    organisation: str | None = None
    contact: str | None = None


# ---------- Helpers ----------


def _validate_severity(severity: str) -> None:
    if severity not in SEVERITIES:
        raise APIError(
            422, ErrorCode.INVALID_INPUT,
            f"severity must be one of {list(SEVERITIES)}",
        )


def _validate_status(status: str) -> None:
    if status not in STATUSES:
        raise APIError(
            422, ErrorCode.INVALID_INPUT,
            f"status must be one of {list(STATUSES)}",
        )


def _require_org(user: dict) -> tuple[uuid.UUID, str]:
    role = user.get("role")
    if role not in {"consumer", "provider"}:
        raise APIError(403, ErrorCode.FORBIDDEN, "Only consumers and providers can manage incidents")
    return user["id"], role


async def _load_owned(
    incident_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> IncidentReport:
    result = await db.execute(
        select(IncidentReport).where(
            IncidentReport.id == incident_id,
            IncidentReport.org_id == org_id,
        )
    )
    inc = result.scalar_one_or_none()
    if inc is None:
        raise APIError(404, ErrorCode.INCIDENT_NOT_FOUND, "Incident not found")
    return inc


async def _load_agent(agent_id: str | None, db: AsyncSession) -> Agent | None:
    if not agent_id:
        return None
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


def _to_response(inc: IncidentReport) -> IncidentResponse:
    deadline = deadline_for(inc.severity, inc.awareness_at)
    remaining = time_remaining(inc.severity, inc.awareness_at)
    return IncidentResponse(
        id=inc.id,
        org_id=inc.org_id,
        agent_id=inc.agent_id,
        agent_version=inc.agent_version,
        task_id=inc.task_id,
        title=inc.title,
        summary=inc.summary,
        severity=inc.severity,
        status=inc.status,
        detected_at=inc.detected_at,
        awareness_at=inc.awareness_at,
        affected_persons_estimate=inc.affected_persons_estimate,
        root_cause=inc.root_cause,
        mitigation_taken=inc.mitigation_taken,
        mitigation_planned=inc.mitigation_planned,
        reported_to_authority_at=inc.reported_to_authority_at,
        authority_name=inc.authority_name,
        authority_reference=inc.authority_reference,
        deadline_at=deadline,
        deadline_days=SEVERITY_DEADLINE_DAYS[inc.severity],
        time_remaining_seconds=int(remaining.total_seconds()),
        overdue=remaining.total_seconds() < 0,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
    )


# ---------- Routes ----------


@router.get("/severities")
async def list_severities(_: dict = Depends(get_current_user)):
    """Public severity catalog with deadlines per category."""
    return {"severities": severity_catalog()}


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List incidents owned by the authenticated organisation."""
    org_id, _ = _require_org(user)
    if status is not None:
        _validate_status(status)
    if severity is not None:
        _validate_severity(severity)

    stmt = select(IncidentReport).where(IncidentReport.org_id == org_id)
    if status:
        stmt = stmt.where(IncidentReport.status == status)
    if severity:
        stmt = stmt.where(IncidentReport.severity == severity)
    if agent_id:
        stmt = stmt.where(IncidentReport.agent_id == agent_id)
    stmt = stmt.order_by(IncidentReport.awareness_at.desc())

    incidents = list((await db.execute(stmt)).scalars().all())
    responses = [_to_response(i) for i in incidents]
    overdue = sum(1 for r in responses if r.overdue and r.status not in {"reported", "resolved", "withdrawn"})
    open_count = sum(1 for i in incidents if i.status in {"draft", "confirmed", "under_investigation"})
    return IncidentListResponse(
        incidents=responses,
        total=len(responses),
        overdue_count=overdue,
        open_count=open_count,
    )


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    req: IncidentCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a new incident."""
    org_id, org_role = _require_org(user)
    _validate_severity(req.severity)

    inc = IncidentReport(
        org_id=org_id,
        org_role=org_role,
        agent_id=req.agent_id,
        agent_version=req.agent_version,
        task_id=req.task_id,
        severity=req.severity,
        status="draft",
        detected_at=req.detected_at,
        awareness_at=req.awareness_at or req.detected_at,
        title=req.title,
        summary=req.summary,
        affected_persons_estimate=req.affected_persons_estimate,
        root_cause=req.root_cause,
        mitigation_taken=req.mitigation_taken,
        mitigation_planned=req.mitigation_planned,
        created_by=str(user["id"]),
        extra=req.extra,
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    return _to_response(inc)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)
    return _to_response(inc)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    req: IncidentUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)

    if req.severity is not None:
        _validate_severity(req.severity)
        inc.severity = req.severity
    if req.status is not None:
        _validate_status(req.status)
        inc.status = req.status
    for attr in (
        "title",
        "summary",
        "detected_at",
        "awareness_at",
        "affected_persons_estimate",
        "root_cause",
        "mitigation_taken",
        "mitigation_planned",
        "extra",
    ):
        value = getattr(req, attr)
        if value is not None:
            setattr(inc, attr, value)

    await db.commit()
    await db.refresh(inc)
    return _to_response(inc)


@router.post("/{incident_id}/report", response_model=IncidentResponse)
async def mark_reported(
    incident_id: uuid.UUID,
    req: ReportedRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark the incident as reported to the MSA."""
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)
    inc.reported_to_authority_at = req.reported_at or datetime.now(timezone.utc)
    inc.authority_name = req.authority_name or inc.authority_name or "BNetzA"
    inc.authority_reference = req.authority_reference or inc.authority_reference
    inc.status = "reported"
    await db.commit()
    await db.refresh(inc)
    return _to_response(inc)


@router.delete("/{incident_id}", status_code=204)
async def delete_incident(
    incident_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)
    await db.delete(inc)
    await db.commit()
    return None


# ---------- Report template exports ----------


@router.post("/{incident_id}/report-template")
async def report_template_json(
    incident_id: uuid.UUID,
    contact: ProviderContactRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)
    agent = await _load_agent(inc.agent_id, db)
    return build_incident_report_template(
        inc,
        agent,
        contact.model_dump(exclude_none=True) if contact else None,
    )


@router.post("/{incident_id}/report-template/markdown", response_class=PlainTextResponse)
async def report_template_markdown(
    incident_id: uuid.UUID,
    contact: ProviderContactRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)
    agent = await _load_agent(inc.agent_id, db)
    report = build_incident_report_template(
        inc,
        agent,
        contact.model_dump(exclude_none=True) if contact else None,
    )
    md = incident_report_to_markdown(report)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="incident-{inc.id}.md"'},
    )


@router.post("/{incident_id}/report-template/pdf")
async def report_template_pdf(
    incident_id: uuid.UUID,
    contact: ProviderContactRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id, _ = _require_org(user)
    inc = await _load_owned(incident_id, org_id, db)
    agent = await _load_agent(inc.agent_id, db)
    report = build_incident_report_template(
        inc,
        agent,
        contact.model_dump(exclude_none=True) if contact else None,
    )
    pdf_bytes = markdown_to_pdf(
        incident_report_to_markdown(report),
        title=f"Incident · {inc.title}",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="incident-{inc.id}.pdf"'},
    )
