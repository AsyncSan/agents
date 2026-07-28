"""Data governance routes (Art. 10)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.data_governance import (
    agent_data_sheet_to_markdown,
    build_agent_data_sheet,
    build_org_data_inventory,
)
from agentforge.db import get_db
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/data-governance", tags=["data-governance"])


class DataSheetRequest(BaseModel):
    agent_id: str | None = None
    manual_agent: ManualAgentInput | None = None
    deployer_source_description: str | None = None
    special_categories_flag: str | None = None
    training_data_statement: str | None = None
    fine_tuning_datasets: str | None = None
    representativeness: str | None = None
    known_gaps: list[str] | None = None
    bias_assessment_method: str | None = None
    mitigation_measures: list[str] | None = None


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


async def _resolve_agent(req: DataSheetRequest, db: AsyncSession):
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


async def _org_agents(user: dict, db: AsyncSession) -> list[Agent]:
    role = user.get("role")
    stmt = select(Agent)
    if role == "provider":
        stmt = stmt.where(Agent.provider_id == user["id"])
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _inputs(req: DataSheetRequest) -> dict[str, Any]:
    skip = {"agent_id", "manual_agent"}
    return {k: v for k, v in req.model_dump().items() if v is not None and k not in skip}


@router.get("/inventory")
async def org_inventory(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated Art. 10 inventory across the caller's agents.

    Consumers see platform-wide aggregation (they are data subjects via inputs
    but not agent owners); providers see only their own agents.
    """
    agents = await _org_agents(user, db)
    return build_org_data_inventory(agents)


@router.post("/agent-sheet")
async def agent_sheet_json(
    req: DataSheetRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(req, db)
    return build_agent_data_sheet(agent, _inputs(req))


@router.post("/agent-sheet/markdown", response_class=PlainTextResponse)
async def agent_sheet_markdown(
    req: DataSheetRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(req, db)
    sheet = build_agent_data_sheet(agent, _inputs(req))
    md = agent_data_sheet_to_markdown(sheet)
    slug = req.agent_id or "manual"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="data-sheet-{slug}.md"'
        },
    )


@router.post("/agent-sheet/pdf")
async def agent_sheet_pdf(
    req: DataSheetRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(req, db)
    sheet = build_agent_data_sheet(agent, _inputs(req))
    pdf_bytes = markdown_to_pdf(
        agent_data_sheet_to_markdown(sheet),
        title=f"Data Sheet · {agent.name}",
    )
    slug = req.agent_id or "manual"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="data-sheet-{slug}.pdf"'
        },
    )


@router.get("/agent-sheet/public/{agent_id}")
async def agent_sheet_public(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(agent_id, db)
    return build_agent_data_sheet(agent, {})
