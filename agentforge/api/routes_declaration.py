"""Declaration of Conformity routes (Art. 47, Annex V)."""

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
from agentforge.declaration import (
    build_declaration,
    declaration_to_markdown,
)
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/declaration", tags=["declaration"])


class DeclarationRequest(BaseModel):
    agent_id: str | None = None
    manual_agent: ManualAgentInput | None = None
    provider_name: str | None = None
    provider_address: str | None = None
    auth_rep_required: bool | None = None
    auth_rep_name: str | None = None
    auth_rep_address: str | None = None
    processes_personal_data: bool | None = None
    dpo_contact: str | None = None
    harmonised_standards: list[str] | None = None
    common_specifications: list[str] | None = None
    standards_notes: str | None = None
    notified_body_required: bool | None = None
    notified_body_name: str | None = None
    notified_body_id: str | None = None
    assessment_procedure: str | None = None
    certificate_reference: str | None = None
    signature_place: str | None = None
    signature_date: str | None = None
    signatory_name: str | None = None
    signatory_function: str | None = None
    signed_on_behalf_of: str | None = None
    signature: str | None = None
    language: str | None = None
    translations_available: list[str] | None = None
    additional_references: list[str] | None = None
    ce_marking_affixed: bool | None = None
    ce_marking_affixed_electronically: bool | None = None


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


async def _resolve_agent(req: DeclarationRequest, db: AsyncSession):
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


def _inputs(req: DeclarationRequest) -> dict[str, Any]:
    skip = {"agent_id", "manual_agent"}
    return {k: v for k, v in req.model_dump().items() if v is not None and k not in skip}


@router.post("/template")
async def create_declaration(
    req: DeclarationRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(req, db)
    return build_declaration(agent, _inputs(req))


@router.post("/template/markdown", response_class=PlainTextResponse)
async def create_declaration_markdown(
    req: DeclarationRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(req, db)
    record = build_declaration(agent, _inputs(req))
    md = declaration_to_markdown(record)
    slug = req.agent_id or "manual"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="declaration-{slug}.md"'
        },
    )


@router.post("/template/pdf")
async def create_declaration_pdf(
    req: DeclarationRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(req, db)
    record = build_declaration(agent, _inputs(req))
    pdf_bytes = markdown_to_pdf(
        declaration_to_markdown(record),
        title=f"EU Declaration of Conformity · {agent.name}",
    )
    slug = req.agent_id or "manual"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="declaration-{slug}.pdf"'
        },
    )


@router.get("/template/public/{agent_id}")
async def public_declaration(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(agent_id, db)
    return build_declaration(agent, {})
