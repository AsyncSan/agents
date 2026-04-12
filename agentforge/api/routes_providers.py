"""Provider routes: public profiles and aggregated stats."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agentforge.api.routes_agents import _agent_to_response
from agentforge.api.schemas import ProviderProfileResponse
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.provider import Provider

router = APIRouter(prefix="/v1/providers", tags=["providers"])


@router.get("/{provider_id}", response_model=ProviderProfileResponse)
async def get_provider_profile(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a provider's public profile with all agents and aggregated stats."""
    result = await db.execute(
        select(Provider)
        .options(selectinload(Provider.agents))
        .where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Aggregated stats across all agents
    stats_result = await db.execute(
        select(
            func.count(Agent.id).label("total"),
            func.count(Agent.id).filter(Agent.status == "active").label("active"),
            func.coalesce(func.sum(Agent.total_executions), 0).label("execs"),
            func.coalesce(func.sum(Agent.success_count), 0).label("success"),
            func.avg(Agent.trust_score).filter(Agent.trust_score.is_not(None)).label("avg_trust"),
        ).where(Agent.provider_id == provider.id)
    )
    row = stats_result.one()

    # Build agent responses (only active agents in public profile)
    agents = [
        _agent_to_response(a)
        for a in provider.agents
        if a.status == "active"
    ]

    return ProviderProfileResponse(
        id=provider.id,
        name=provider.name,
        signing_public_key=provider.signing_public_key,
        total_agents=row[0] or 0,
        active_agents=row[1] or 0,
        total_executions=row[2] or 0,
        total_success=row[3] or 0,
        avg_trust_score=round(float(row[4]), 2) if row[4] else None,
        agents=agents,
        created_at=provider.created_at,
    )
