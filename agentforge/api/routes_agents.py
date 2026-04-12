"""Agent routes: CRUD, discovery, stats, and health for capability cards."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String as SAString
from sqlalchemy import cast, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agentforge.api.auth import require_role
from agentforge.api.schemas import (
    AgentCreateRequest,
    AgentHealthResponse,
    AgentListResponse,
    AgentResponse,
    AgentStatsResponse,
    AgentVersionListResponse,
    AgentVersionResponse,
    CategoryItem,
    CategoryListResponse,
    FeaturedAgentResponse,
    FeaturedListResponse,
    RecentExecution,
)
from agentforge.db import get_db
from agentforge.events import emit_event
from agentforge.models.agent import Agent
from agentforge.models.agent_version import AgentVersion
from agentforge.models.execution import Execution
from agentforge.models.provider import Provider
from agentforge.models.task import Task
from agentforge.signing import sign_card, verify_card

router = APIRouter(prefix="/v1/agents", tags=["agents"])


def _agent_to_response(
    agent: Agent,
    provider_name: str | None = None,
    include_instructions: bool = False,
) -> AgentResponse:
    """Convert Agent model to response. Strips instructions by default (public)."""
    pname = provider_name
    if pname is None:
        try:
            pname = agent.provider.name if agent.provider else None
        except Exception:
            pname = None

    card = dict(agent.card)
    if not include_instructions:
        card.pop("instructions", None)

    # Get provider's public key for verification
    pub_key = None
    try:
        if agent.provider and agent.provider.signing_public_key:
            pub_key = agent.provider.signing_public_key
    except Exception:
        pass

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        provider_id=agent.provider_id,
        provider_name=pname,
        status=agent.status,
        version=agent.version,
        card=card,
        signature=agent.signature,
        signing_public_key=pub_key,
        trust_score=float(agent.trust_score) if agent.trust_score else None,
        total_executions=agent.total_executions,
        success_count=agent.success_count,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


_SORT_OPTIONS = {
    "trust": Agent.trust_score.desc().nulls_last(),
    "price": Agent.card["pricing"]["base_price_usd"].as_float().asc(),
    "executions": Agent.total_executions.desc(),
    "newest": Agent.created_at.desc(),
}


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    """List all domains and tags with agent counts."""
    domain_col = Agent.card["capabilities"]["domain"].as_string().label("domain")
    result = await db.execute(
        select(domain_col, func.count().label("cnt"))
        .where(Agent.status == "active")
        .group_by(domain_col)
    )
    domains = [CategoryItem(name=row[0], count=row[1]) for row in result.all()]

    # Collect tag counts via unnest
    tag_result = await db.execute(
        text(
            "SELECT tag, COUNT(*) FROM agents, "
            "jsonb_array_elements_text(card->'capabilities'->'tags') AS tag "
            "WHERE status = 'active' GROUP BY tag ORDER BY count DESC"
        )
    )
    tags = [CategoryItem(name=row[0], count=row[1]) for row in tag_result.all()]

    return CategoryListResponse(domains=domains, tags=tags)


@router.get("/featured", response_model=FeaturedListResponse)
async def featured_agents(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get featured agents: trending, top-rated, and newest."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Trending: agents with most recent executions, weighted by trust
    trending_query = (
        select(
            Agent,
            func.count(Task.id).label("recent_execs"),
        )
        .outerjoin(Task, (Task.agent_id == Agent.id) & (Task.created_at >= week_ago))
        .where(Agent.status == "active")
        .group_by(Agent.id)
        .having(func.count(Task.id) > 0)
        .order_by(
            (
                func.count(Task.id) * func.coalesce(Agent.trust_score, literal(0.5))
            ).desc()
        )
        .options(selectinload(Agent.provider))
        .limit(limit)
    )
    result = await db.execute(trending_query)
    trending_rows = result.all()
    trending = []
    for row in trending_rows:
        agent = row[0]
        recent_execs = row[1]
        trust = float(agent.trust_score) if agent.trust_score else 0.5
        score = recent_execs * trust
        trending.append(
            FeaturedAgentResponse(
                agent=_agent_to_response(agent),
                trending_score=round(score, 2),
            )
        )

    # Top rated by trust score
    top_result = await db.execute(
        select(Agent)
        .where(Agent.status == "active", Agent.trust_score.is_not(None))
        .options(selectinload(Agent.provider))
        .order_by(Agent.trust_score.desc())
        .limit(limit)
    )
    top_rated = [_agent_to_response(a) for a in top_result.scalars().all()]

    # Newest
    new_result = await db.execute(
        select(Agent)
        .where(Agent.status == "active")
        .options(selectinload(Agent.provider))
        .order_by(Agent.created_at.desc())
        .limit(limit)
    )
    newest = [_agent_to_response(a) for a in new_result.scalars().all()]

    return FeaturedListResponse(trending=trending, top_rated=top_rated, newest=newest)


@router.get("/{agent_id}/stats", response_model=AgentStatsResponse)
async def agent_stats(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed execution statistics for an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Total revenue from completed tasks
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Task.amount_captured_cents), 0)).where(
            Task.agent_id == agent_id, Task.payment_status == "captured"
        )
    )
    total_revenue = revenue_result.scalar()

    # Recent executions (last 20)
    exec_result = await db.execute(
        select(Execution)
        .join(Task, Task.id == Execution.task_id)
        .where(Task.agent_id == agent_id)
        .order_by(Execution.created_at.desc())
        .limit(20)
    )
    recent = [
        RecentExecution(
            execution_id=e.id,
            task_id=e.task_id,
            status=e.status,
            elapsed_seconds=e.elapsed_seconds,
            created_at=e.created_at,
        )
        for e in exec_result.scalars().all()
    ]

    failure_count = agent.total_executions - agent.success_count
    success_rate = (
        agent.success_count / agent.total_executions if agent.total_executions > 0 else 0.0
    )

    return AgentStatsResponse(
        agent_id=agent_id,
        total_executions=agent.total_executions,
        success_count=agent.success_count,
        failure_count=failure_count,
        success_rate=round(success_rate, 4),
        avg_duration_seconds=(
            float(agent.avg_duration_seconds) if agent.avg_duration_seconds else None
        ),
        total_revenue_cents=total_revenue,
        trust_score=float(agent.trust_score) if agent.trust_score else None,
        recent_executions=recent,
    )


@router.get("/{agent_id}/health", response_model=AgentHealthResponse)
async def agent_health(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get health status for an agent based on recent execution patterns."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    # Last execution timestamp
    last_exec_result = await db.execute(
        select(Execution.completed_at)
        .join(Task, Task.id == Execution.task_id)
        .where(Task.agent_id == agent_id)
        .order_by(Execution.completed_at.desc().nulls_last())
        .limit(1)
    )
    last_exec_at = last_exec_result.scalar_one_or_none()

    # 24h stats
    stats_24h = await db.execute(
        select(
            func.count(Execution.id).label("total"),
            func.count(Execution.id).filter(Execution.status == "completed").label("success"),
            func.avg(Execution.elapsed_seconds).filter(
                Execution.status == "completed"
            ).label("avg_dur"),
        )
        .join(Task, Task.id == Execution.task_id)
        .where(Task.agent_id == agent_id, Execution.created_at >= day_ago)
    )
    row = stats_24h.one()
    total_24h = row[0] or 0
    success_24h = row[1] or 0
    avg_dur_24h = float(row[2]) if row[2] else None
    rate_24h = success_24h / total_24h if total_24h > 0 else None

    # Consecutive failures (count from most recent backwards)
    recent_statuses = await db.execute(
        select(Execution.status)
        .join(Task, Task.id == Execution.task_id)
        .where(Task.agent_id == agent_id)
        .order_by(Execution.created_at.desc())
        .limit(20)
    )
    consecutive_failures = 0
    for (s,) in recent_statuses.all():
        if s == "failed":
            consecutive_failures += 1
        else:
            break

    # Determine health status
    if agent.total_executions == 0:
        health_status = "dormant"
        uptime = "new"
    elif consecutive_failures >= 5:
        health_status = "unhealthy"
        uptime = "active"
    elif consecutive_failures >= 2 or (rate_24h is not None and rate_24h < 0.5):
        health_status = "degraded"
        uptime = "active"
    else:
        health_status = "healthy"
        # Idle if no executions in 7 days
        if last_exec_at and (now - last_exec_at).days > 7:
            uptime = "idle"
        else:
            uptime = "active"

    return AgentHealthResponse(
        agent_id=agent_id,
        status=health_status,
        last_execution_at=last_exec_at,
        consecutive_failures=consecutive_failures,
        success_rate_24h=round(rate_24h, 4) if rate_24h is not None else None,
        avg_duration_24h=round(avg_dur_24h, 2) if avg_dur_24h else None,
        executions_24h=total_24h,
        uptime_status=uptime,
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    q: str | None = None,
    domain: str | None = None,
    tag: str | None = None,
    min_trust: float | None = Query(None, ge=0, le=1),
    max_price_usd: float | None = Query(None, ge=0),
    status: str = "active",
    sort_by: str = Query("executions", pattern="^(trust|price|executions|newest)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Discover agents with search, filtering, and sorting."""
    query = select(Agent).where(Agent.status == status)

    # Text search across name, description, tags
    if q:
        like_pattern = f"%{q}%"
        query = query.where(
            or_(
                Agent.name.ilike(like_pattern),
                Agent.description.ilike(like_pattern),
                cast(Agent.card["capabilities"]["tags"], SAString).ilike(like_pattern),
            )
        )

    if domain:
        query = query.where(Agent.card["capabilities"]["domain"].as_string() == domain)
    if tag:
        query = query.where(Agent.card["capabilities"]["tags"].contains([tag]))
    if min_trust is not None:
        query = query.where(Agent.trust_score >= min_trust)
    if max_price_usd is not None:
        query = query.where(
            Agent.card["pricing"]["base_price_usd"].as_float() <= max_price_usd
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    sort_clause = _SORT_OPTIONS.get(sort_by, Agent.total_executions.desc())
    query = (
        query.options(selectinload(Agent.provider))
        .order_by(sort_clause)
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

    # Sign the card if provider has a signing key
    signature = None
    provider_result = await db.execute(
        select(Provider).where(Provider.id == user["id"])
    )
    provider = provider_result.scalar_one_or_none()
    if provider and provider.signing_private_key:
        signature = sign_card(card, provider.signing_private_key)

    agent = Agent(
        id=req.id,
        provider_id=user["id"],
        name=req.name,
        description=req.description,
        card=card,
        signature=signature,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    await emit_event(
        db,
        "agent.created",
        actor_id=str(user["id"]),
        actor_role="provider",
        resource_type="agent",
        resource_id=req.id,
        payload={"name": req.name, "domain": req.domain},
    )
    await db.commit()

    return _agent_to_response(agent, provider_name=user["name"], include_instructions=True)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    req: AgentCreateRequest,
    user: dict = Depends(require_role("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing agent capability card. Archives previous version."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.provider_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your agent")

    # Archive current version before overwriting
    archive = AgentVersion(
        agent_id=agent.id,
        version=agent.version,
        card=dict(agent.card),
        signature=agent.signature,
        change_summary=f"Superseded by v{agent.version + 1}",
    )
    db.add(archive)

    new_version = agent.version + 1

    card = {
        "kind": "AgentCapabilityCard",
        "version": new_version,
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

    # Re-sign on update
    provider_result = await db.execute(
        select(Provider).where(Provider.id == user["id"])
    )
    provider = provider_result.scalar_one_or_none()
    if provider and provider.signing_private_key:
        agent.signature = sign_card(card, provider.signing_private_key)

    agent.name = req.name
    agent.description = req.description
    agent.card = card
    agent.version = new_version
    await db.commit()
    await db.refresh(agent)

    await emit_event(
        db,
        "agent.updated",
        actor_id=str(user["id"]),
        actor_role="provider",
        resource_type="agent",
        resource_id=agent_id,
        payload={"name": req.name, "version": new_version},
    )
    await db.commit()

    return _agent_to_response(agent, provider_name=user["name"], include_instructions=True)


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
    await emit_event(
        db,
        "agent.deleted",
        actor_id=str(user["id"]),
        actor_role="provider",
        resource_type="agent",
        resource_id=agent_id,
    )
    await db.commit()


@router.get("/{agent_id}/verify")
async def verify_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Verify the authenticity of an agent's capability card signature."""
    result = await db.execute(
        select(Agent).options(selectinload(Agent.provider)).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not agent.signature:
        return {"verified": False, "reason": "no_signature", "agent_id": agent_id}

    pub_key = agent.provider.signing_public_key if agent.provider else None
    if not pub_key:
        return {"verified": False, "reason": "no_public_key", "agent_id": agent_id}

    valid = verify_card(agent.card, agent.signature, pub_key)
    return {
        "verified": valid,
        "agent_id": agent_id,
        "signing_public_key": pub_key,
        "reason": None if valid else "signature_mismatch",
    }


@router.get("/{agent_id}/versions", response_model=AgentVersionListResponse)
async def list_agent_versions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all archived versions of an agent's capability card."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version.desc())
    )
    versions = [
        AgentVersionResponse(
            id=v.id,
            agent_id=v.agent_id,
            version=v.version,
            card=v.card,
            signature=v.signature,
            change_summary=v.change_summary,
            created_at=v.created_at,
        )
        for v in result.scalars().all()
    ]

    return AgentVersionListResponse(
        versions=versions,
        current_version=agent.version,
    )
