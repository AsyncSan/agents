"""Public read-only audit endpoints. No login; token in the URL path.

Every endpoint loads an ``AuditShare`` by token hash, checks it is
active, scopes queries by the share's ``org_id`` (and optionally its
``scope_agent_id``), and bumps an access counter on each call. Only
read operations are exposed; there is no state-changing endpoint on
this router.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.errors import APIError, ErrorCode
from agentforge.audit_shares import hash_token, is_active
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.audit_share import AuditShare
from agentforge.models.compliance_document import ComplianceDocument
from agentforge.models.event_log import EventLog
from agentforge.models.incident import IncidentReport
from agentforge.models.modification import ModificationRecord
from agentforge.models.oversight import OversightAssignment
from agentforge.oversight import build_agent_oversight_roster

router = APIRouter(prefix="/v1/audit", tags=["audit-view"])


async def _resolve_share(token: str, db: AsyncSession) -> AuditShare:
    """Load + validate share, bump access counter. Token is raw, as in URL."""
    token_hash = hash_token(token)
    result = await db.execute(
        select(AuditShare).where(AuditShare.token_hash == token_hash)
    )
    share = result.scalar_one_or_none()
    if share is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Share not found")
    if not is_active(share.expires_at, share.revoked_at):
        raise APIError(410, ErrorCode.FORBIDDEN, "Share expired or revoked")

    share.access_count += 1
    share.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(share)
    return share


def _check_agent_scope(share: AuditShare, agent_id: str) -> None:
    if share.scope_agent_id is not None and share.scope_agent_id != agent_id:
        raise APIError(
            403,
            ErrorCode.FORBIDDEN,
            "This share is scoped to a single agent that does not match the request.",
        )


@router.get("/{token}/profile")
async def profile(token: str, db: AsyncSession = Depends(get_db)):
    share = await _resolve_share(token, db)
    agents_stmt = select(Agent)
    if share.scope_agent_id is not None:
        agents_stmt = agents_stmt.where(Agent.id == share.scope_agent_id)
    else:
        # Provider-owned shares: filter by provider.
        if share.org_role == "provider":
            agents_stmt = agents_stmt.where(Agent.provider_id == share.org_id)
        # Consumer shares: no provider filter (they observe their deployed
        # agents via compliance docs / event log scoped on actor_id).
    agents = list((await db.execute(agents_stmt)).scalars().all())

    return {
        "share": {
            "label": share.label,
            "auditor_name": share.auditor_name,
            "auditor_organisation": share.auditor_organisation,
            "expires_at": share.expires_at.isoformat(),
            "org_role": share.org_role,
            "scope_agent_id": share.scope_agent_id,
            "access_count": share.access_count,
        },
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "version": a.version,
                "risk_class": a.risk_class,
                "status": a.status,
            }
            for a in agents
        ],
    }


@router.get("/{token}/documents")
async def list_documents(
    token: str,
    doc_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    share = await _resolve_share(token, db)
    stmt = select(ComplianceDocument).where(ComplianceDocument.org_id == share.org_id)
    if share.scope_agent_id is not None:
        stmt = stmt.where(ComplianceDocument.agent_id == share.scope_agent_id)
    if doc_type:
        stmt = stmt.where(ComplianceDocument.doc_type == doc_type)
    stmt = stmt.order_by(ComplianceDocument.updated_at.desc()).limit(200)
    docs = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "title": d.title,
            "agent_id": d.agent_id,
            "agent_version": d.agent_version,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
            "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        }
        for d in docs
    ]


@router.get("/{token}/documents/{doc_id}")
async def get_document(
    token: str,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    share = await _resolve_share(token, db)
    result = await db.execute(
        select(ComplianceDocument).where(
            ComplianceDocument.id == doc_id, ComplianceDocument.org_id == share.org_id
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise APIError(404, ErrorCode.DOCUMENT_NOT_FOUND, "Document not found")
    if share.scope_agent_id is not None and doc.agent_id != share.scope_agent_id:
        raise APIError(403, ErrorCode.FORBIDDEN, "Out of scope for this share")
    return {
        "id": str(doc.id),
        "doc_type": doc.doc_type,
        "title": doc.title,
        "agent_id": doc.agent_id,
        "agent_version": doc.agent_version,
        "status": doc.status,
        "payload": doc.payload,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
        "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
    }


@router.get("/{token}/events")
async def list_events(
    token: str,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    share = await _resolve_share(token, db)
    stmt = select(EventLog).where(EventLog.actor_id == str(share.org_id))
    if share.scope_agent_id is not None:
        stmt = stmt.where(EventLog.resource_id == share.scope_agent_id)
    stmt = stmt.order_by(desc(EventLog.created_at)).limit(limit)
    events = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "actor_role": e.actor_role,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "payload": e.payload,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


async def _load_agent_in_scope(
    share: AuditShare, agent_id: str, db: AsyncSession
) -> Agent:
    _check_agent_scope(share, agent_id)
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    if share.org_role == "provider" and agent.provider_id != share.org_id:
        raise APIError(403, ErrorCode.FORBIDDEN, "Agent outside this share's org")
    return agent


@router.get("/{token}/modifications/{agent_id}")
async def list_modifications(
    token: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    share = await _resolve_share(token, db)
    await _load_agent_in_scope(share, agent_id, db)
    rows = list(
        (
            await db.execute(
                select(ModificationRecord)
                .where(ModificationRecord.agent_id == agent_id)
                .order_by(desc(ModificationRecord.created_at))
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
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
            "diff": r.diff,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{token}/oversight/{agent_id}")
async def get_oversight(
    token: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    share = await _resolve_share(token, db)
    agent = await _load_agent_in_scope(share, agent_id, db)
    stmt = (
        select(OversightAssignment)
        .where(OversightAssignment.org_id == share.org_id)
        .where(OversightAssignment.active.is_(True))
    )
    assignments = list((await db.execute(stmt)).scalars().all())
    assignments_dicts: list[dict[str, Any]] = [
        {
            "staff_name": a.staff_name,
            "staff_email": a.staff_email,
            "staff_role_title": a.staff_role_title,
            "oversight_role": a.oversight_role,
            "authority_level": a.authority_level,
            "assigned_agent_ids": a.assigned_agent_ids,
            "training_certificates": a.training_certificates or [],
            "competence_notes": a.competence_notes,
            "authority_source": a.authority_source,
            "active": a.active,
        }
        for a in assignments
    ]
    return build_agent_oversight_roster(
        agent.id, agent.name, agent.risk_class or "minimal", assignments_dicts
    )


@router.get("/{token}/incidents")
async def list_incidents(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    share = await _resolve_share(token, db)
    stmt = select(IncidentReport).where(IncidentReport.org_id == share.org_id)
    if share.scope_agent_id is not None:
        stmt = stmt.where(IncidentReport.agent_id == share.scope_agent_id)
    stmt = stmt.order_by(desc(IncidentReport.detected_at)).limit(200)
    rows = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "id": str(r.id),
            "agent_id": r.agent_id,
            "severity": r.severity,
            "status": r.status,
            "title": r.title,
            "summary": r.summary,
            "detected_at": r.detected_at.isoformat() if r.detected_at else None,
            "reported_to_authority_at": (
                r.reported_to_authority_at.isoformat()
                if r.reported_to_authority_at
                else None
            ),
            "authority_name": r.authority_name,
        }
        for r in rows
    ]
