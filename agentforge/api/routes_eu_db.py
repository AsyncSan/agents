"""EU database registration routes (Art. 49, Annex VIII)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.eu_db import (
    STATUSES,
    build_eu_db_registration,
    eu_db_to_markdown,
)
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/eu-db", tags=["eu-db"])


class RegistrationRequest(BaseModel):
    agent_id: str | None = None
    manual_agent: ManualAgentInput | None = None
    provider_name: str | None = None
    provider_address: str | None = None
    provider_contact: str | None = None
    submitter_name: str | None = None
    submitter_relationship: str | None = None
    auth_rep_required: bool | None = None
    auth_rep_name: str | None = None
    auth_rep_mandate_reference: str | None = None
    trade_name: str | None = None
    additional_identifiers: list[str] | None = None
    status: str | None = None
    placed_on_market_date: str | None = None
    withdrawal_date: str | None = None
    withdrawal_reason: str | None = None
    software_type: str | None = None
    member_states: list[str] | None = None
    doc_reference: str | None = None
    ce_marking_affixed: bool | None = None
    ifu_url: str | None = None
    additional_info_url: str | None = None
    non_high_risk_justification: str | None = None


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


async def _resolve_agent(req: RegistrationRequest, db: AsyncSession):
    if req.manual_agent is not None:
        try:
            return build_manual_agent(req.manual_agent)
        except ValueError as exc:
            raise APIError(422, ErrorCode.INVALID_INPUT, str(exc)) from exc
    if not req.agent_id:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            "Provide either agent_id (platform agent) or manual_agent (external system).",
        )
    return await _load_agent(req.agent_id, db)


def _inputs(req: RegistrationRequest) -> dict[str, Any]:
    skip = {"agent_id", "manual_agent"}
    return {k: v for k, v in req.model_dump().items() if v is not None and k not in skip}


def _validate_status(status: str) -> None:
    if status not in STATUSES:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"status must be one of {list(STATUSES)}",
        )


@router.get("/statuses")
async def list_statuses():
    return {"statuses": list(STATUSES)}


@router.post("/registration")
async def create_registration(
    req: RegistrationRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.status is not None:
        _validate_status(req.status)
    agent = await _resolve_agent(req, db)
    return build_eu_db_registration(agent, _inputs(req))


@router.post("/registration/markdown", response_class=PlainTextResponse)
async def create_registration_markdown(
    req: RegistrationRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.status is not None:
        _validate_status(req.status)
    agent = await _resolve_agent(req, db)
    record = build_eu_db_registration(agent, _inputs(req))
    md = eu_db_to_markdown(record)
    slug = req.agent_id or "manual"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="eu-db-{slug}.md"'
        },
    )


@router.post("/registration/pdf")
async def create_registration_pdf(
    req: RegistrationRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.status is not None:
        _validate_status(req.status)
    agent = await _resolve_agent(req, db)
    record = build_eu_db_registration(agent, _inputs(req))
    pdf_bytes = markdown_to_pdf(
        eu_db_to_markdown(record),
        title=f"EU DB registration · {agent.name}",
    )
    slug = req.agent_id or "manual"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="eu-db-{slug}.pdf"'
        },
    )


@router.get("/registration/public/{agent_id}")
async def public_registration(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(agent_id, db)
    return build_eu_db_registration(agent, {})
