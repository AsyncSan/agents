"""Post-Market Monitoring Plan routes (Art. 72)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf
from agentforge.pmm_plan import (
    REVIEW_CADENCES,
    build_pmm_plan_template,
    pmm_plan_to_markdown,
)

router = APIRouter(prefix="/v1/pmm", tags=["pmm"])


class PMMRequest(BaseModel):
    agent_id: str | None = None
    manual_agent: ManualAgentInput | None = None
    review_cadence: str = Field(default="monthly")
    pmm_owner: str | None = None
    escalation_chain: list[str] | None = None
    additional_data_sources: list[dict[str, str]] | None = None
    metrics: list[dict[str, Any]] | None = None
    analysis_methodology: str | None = None
    re_assessment_triggers: list[str] | None = None
    corrective_action_procedure: list[str] | None = None


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


async def _resolve_agent(req: PMMRequest, db: AsyncSession):
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


def _inputs(req: PMMRequest) -> dict[str, Any]:
    skip = {"agent_id", "manual_agent"}
    return {k: v for k, v in req.model_dump().items() if v is not None and k not in skip}


def _validate_cadence(cadence: str) -> None:
    if cadence not in REVIEW_CADENCES:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"review_cadence must be one of {list(REVIEW_CADENCES)}",
        )


@router.get("/cadences")
async def list_cadences(_: dict = Depends(get_current_user)):
    return {"cadences": list(REVIEW_CADENCES)}


@router.post("/template")
async def create_pmm_template(
    req: PMMRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_cadence(req.review_cadence)
    agent = await _resolve_agent(req, db)
    return build_pmm_plan_template(agent, _inputs(req))


@router.post("/template/markdown", response_class=PlainTextResponse)
async def create_pmm_markdown(
    req: PMMRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_cadence(req.review_cadence)
    agent = await _resolve_agent(req, db)
    plan = build_pmm_plan_template(agent, _inputs(req))
    md = pmm_plan_to_markdown(plan)
    slug = req.agent_id or "manual"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="pmm-plan-{slug}.md"'
        },
    )


@router.post("/template/pdf")
async def create_pmm_pdf(
    req: PMMRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_cadence(req.review_cadence)
    agent = await _resolve_agent(req, db)
    plan = build_pmm_plan_template(agent, _inputs(req))
    pdf_bytes = markdown_to_pdf(
        pmm_plan_to_markdown(plan), title=f"PMM Plan · {agent.name}"
    )
    slug = req.agent_id or "manual"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="pmm-plan-{slug}.pdf"'
        },
    )


@router.get("/template/public/{agent_id}")
async def public_pmm_template(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await _load_agent(agent_id, db)
    return build_pmm_plan_template(agent, {})
