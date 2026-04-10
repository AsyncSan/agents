"""Agent routes: CRUD for capability cards."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agentforge.api.auth import require_role
from agentforge.api.schemas import (
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
)
from agentforge.db import get_db
from agentforge.models.agent import Agent

router = APIRouter(prefix="/v1/agents", tags=["agents"])


def _agent_to_response(agent: Agent, provider_name: str | None = None) -> AgentResponse:
    # provider_name can be passed explicitly to avoid lazy-loading issues
    pname = provider_name
    if pname is None:
        try:
            pname = agent.provider.name if agent.provider else None
        except Exception:
            pname = None
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        provider_id=agent.provider_id,
        provider_name=pname,
        status=agent.status,
        card=agent.card,
        trust_score=float(agent.trust_score) if agent.trust_score else None,
        total_executions=agent.total_executions,
        success_count=agent.success_count,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    domain: str | None = None,
    tag: str | None = None,
    status: str = "active",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List agents with optional filters."""
    query = select(Agent).where(Agent.status == status)

    if domain:
        query = query.where(Agent.card["capabilities"]["domain"].as_string() == domain)
    if tag:
        query = query.where(Agent.card["capabilities"]["tags"].contains([tag]))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = (
        query.options(selectinload(Agent.provider))
        .order_by(Agent.total_executions.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    agents = result.scalars().all()

    return AgentListResponse(
        agents=[_agent_to_response(a) for a in agents],
        total=total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get agent details including trust score."""
    result = await db.execute(
        select(Agent).options(selectinload(Agent.provider)).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_response(agent)


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    req: AgentCreateRequest,
    user: dict = Depends(require_role("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Register a new agent capability card."""
    # Check for duplicate ID
    existing = await db.execute(select(Agent).where(Agent.id == req.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent ID already exists")

    card = {
        "kind": "AgentCapabilityCard",
        "version": 1,
        "meta": {"id": req.id, "name": req.name, "provider": str(user["id"])},
        "capabilities": {
            "domain": req.domain,
            "tags": req.tags,
            "description": req.description,
            "inputs": [i.model_dump() for i in req.inputs],
            "outputs": [o.model_dump() for o in req.outputs],
            "constraints": req.constraints.model_dump(),
        },
        "runtime": req.runtime.model_dump(),
        "pricing": req.pricing.model_dump(),
        "instructions": req.instructions,
    }

    agent = Agent(
        id=req.id,
        provider_id=user["id"],
        name=req.name,
        description=req.description,
        card=card,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return _agent_to_response(agent, provider_name=user["name"])


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    req: AgentCreateRequest,
    user: dict = Depends(require_role("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing agent capability card."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.provider_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your agent")

    agent.name = req.name
    agent.description = req.description
    agent.card = {
        "kind": "AgentCapabilityCard",
        "version": 1,
        "meta": {"id": req.id, "name": req.name, "provider": str(user["id"])},
        "capabilities": {
            "domain": req.domain,
            "tags": req.tags,
            "description": req.description,
            "inputs": [i.model_dump() for i in req.inputs],
            "outputs": [o.model_dump() for o in req.outputs],
            "constraints": req.constraints.model_dump(),
        },
        "runtime": req.runtime.model_dump(),
        "pricing": req.pricing.model_dump(),
        "instructions": req.instructions,
    }
    await db.commit()
    await db.refresh(agent)
    return _agent_to_response(agent, provider_name=user["name"])


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    user: dict = Depends(require_role("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an agent (set status to deprecated)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.provider_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your agent")
    agent.status = "deprecated"
    await db.commit()
