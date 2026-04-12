"""Platform routes: system health, metrics, and event log."""

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.schemas import (
    ComponentHealth,
    EventLogEntry,
    EventLogResponse,
    PlatformHealthResponse,
)
from agentforge.config import settings
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.event_log import EventLog
from agentforge.models.execution import Execution
from agentforge.models.task import Task

router = APIRouter(tags=["platform"])


@router.get("/v1/platform/health", response_model=PlatformHealthResponse)
async def platform_health(db: AsyncSession = Depends(get_db)):
    """System-wide health check with component status."""
    components = []
    overall = "ok"

    # Database health
    try:
        t0 = time.monotonic()
        await db.execute(text("SELECT 1"))
        db_ms = (time.monotonic() - t0) * 1000
        components.append(
            ComponentHealth(name="database", status="ok", latency_ms=round(db_ms, 1))
        )
    except Exception as e:
        components.append(
            ComponentHealth(name="database", status="down", details=str(e))
        )
        overall = "down"

    # Hetzner API health (just check if token is configured)
    if settings.hcloud_token:
        components.append(
            ComponentHealth(name="compute", status="ok", details="hcloud configured")
        )
    else:
        components.append(
            ComponentHealth(name="compute", status="degraded", details="hcloud token not set")
        )
        if overall == "ok":
            overall = "degraded"

    # Stripe health
    if settings.stripe_secret_key:
        components.append(
            ComponentHealth(name="payments", status="ok", details="stripe configured")
        )
    else:
        components.append(
            ComponentHealth(
                name="payments", status="degraded", details="stripe not configured"
            )
        )
        if overall == "ok":
            overall = "degraded"

    # Worker status (check if dispatch worker is enabled)
    worker_status = "ok" if settings.hcloud_token else "degraded"
    components.append(
        ComponentHealth(name="worker", status=worker_status)
    )

    # Counts
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    pending_result = await db.execute(
        select(func.count()).select_from(Task).where(Task.status == "pending")
    )
    pending_tasks = pending_result.scalar() or 0

    agent_count_result = await db.execute(
        select(func.count()).select_from(Agent).where(Agent.status == "active")
    )
    total_agents = agent_count_result.scalar() or 0

    exec_24h_result = await db.execute(
        select(func.count())
        .select_from(Execution)
        .where(Execution.created_at >= day_ago)
    )
    total_execs_24h = exec_24h_result.scalar() or 0

    return PlatformHealthResponse(
        status=overall,
        version="0.1.0",
        components=components,
        active_workers=1 if settings.hcloud_token else 0,
        pending_tasks=pending_tasks,
        total_agents=total_agents,
        total_executions_24h=total_execs_24h,
    )


@router.get("/v1/events", response_model=EventLogResponse)
async def list_events(
    event_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query the event log. Scoped to the authenticated user's events."""
    query = select(EventLog).order_by(EventLog.created_at.desc())

    # Scope to user's events (actor or resource owner)
    query = query.where(EventLog.actor_id == str(user["id"]))

    if event_type:
        query = query.where(EventLog.event_type == event_type)
    if resource_type:
        query = query.where(EventLog.resource_type == resource_type)
    if resource_id:
        query = query.where(EventLog.resource_id == resource_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query.offset(offset).limit(limit))
    events = [
        EventLogEntry(
            id=e.id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_role=e.actor_role,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]

    return EventLogResponse(events=events, total=total)
