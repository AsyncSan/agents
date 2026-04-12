"""Schedule routes: recurring agent task execution."""

from datetime import datetime, timezone

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import require_role
from agentforge.api.schemas import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
)
from agentforge.db import get_db
from agentforge.events import emit_event
from agentforge.models.agent import Agent
from agentforge.models.schedule import Schedule

router = APIRouter(prefix="/v1/schedules", tags=["schedules"])


def _compute_next_run(cron_expr: str, tz: str = "UTC") -> str:
    """Compute next run time from cron expression."""
    now = datetime.now(timezone.utc)
    cron = croniter(cron_expr, now)
    return cron.get_next(datetime).isoformat()


def _schedule_to_response(s: Schedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id,
        consumer_id=s.consumer_id,
        agent_id=s.agent_id,
        name=s.name,
        cron_expression=s.cron_expression,
        timezone=s.timezone,
        inputs=s.inputs,
        constraints=s.constraints,
        callback_url=s.callback_url,
        active=s.active,
        total_runs=s.total_runs,
        last_run_at=s.last_run_at,
        next_run_at=s.next_run_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    req: ScheduleCreateRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Create a recurring schedule for an agent task."""
    # Validate cron expression
    try:
        croniter(req.cron_expression)
    except (ValueError, KeyError):
        raise HTTPException(status_code=422, detail="Invalid cron expression")

    # Verify agent exists and is active
    agent_result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent or agent.status != "active":
        raise HTTPException(status_code=404, detail="Agent not found or inactive")

    # Budget check
    agent_price = agent.card.get("pricing", {}).get("base_price_usd", 0)
    budget_cap = req.constraints.max_cost_usd
    if budget_cap is not None and agent_price > budget_cap:
        raise HTTPException(
            status_code=400,
            detail=f"Agent price ${agent_price:.2f} exceeds budget ${budget_cap:.2f}",
        )

    # Limit to 20 active schedules per consumer
    count_result = await db.execute(
        select(func.count())
        .select_from(Schedule)
        .where(Schedule.consumer_id == user["id"], Schedule.active.is_(True))
    )
    if (count_result.scalar() or 0) >= 20:
        raise HTTPException(status_code=429, detail="Maximum 20 active schedules")

    next_run = _compute_next_run(req.cron_expression, req.timezone)

    constraints_dict = {}
    if req.constraints.timeout:
        constraints_dict["timeout"] = req.constraints.timeout
    if req.constraints.max_cost_usd is not None:
        constraints_dict["max_cost_usd"] = req.constraints.max_cost_usd

    schedule = Schedule(
        consumer_id=user["id"],
        agent_id=req.agent_id,
        name=req.name,
        cron_expression=req.cron_expression,
        timezone=req.timezone,
        inputs=req.inputs or {},
        constraints=constraints_dict or None,
        callback_url=req.callback_url,
        next_run_at=next_run,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    await emit_event(
        db,
        "schedule.created",
        actor_id=str(user["id"]),
        actor_role="consumer",
        resource_type="schedule",
        resource_id=str(schedule.id),
        payload={"agent_id": req.agent_id, "cron": req.cron_expression},
    )
    await db.commit()

    return _schedule_to_response(schedule)


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    active_only: bool = Query(True),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """List schedules for the authenticated consumer."""
    query = select(Schedule).where(Schedule.consumer_id == user["id"])
    if active_only:
        query = query.where(Schedule.active.is_(True))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.order_by(Schedule.created_at.desc()).offset(offset).limit(limit)
    )
    schedules = [_schedule_to_response(s) for s in result.scalars().all()]

    return ScheduleListResponse(schedules=schedules, total=total)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Get schedule details."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your schedule")
    return _schedule_to_response(schedule)


@router.patch("/{schedule_id}/pause", response_model=ScheduleResponse)
async def pause_schedule(
    schedule_id: str,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Pause a schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your schedule")
    schedule.active = False
    await db.commit()
    await db.refresh(schedule)
    return _schedule_to_response(schedule)


@router.patch("/{schedule_id}/resume", response_model=ScheduleResponse)
async def resume_schedule(
    schedule_id: str,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your schedule")
    schedule.active = True
    schedule.next_run_at = _compute_next_run(schedule.cron_expression, schedule.timezone)
    await db.commit()
    await db.refresh(schedule)
    return _schedule_to_response(schedule)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your schedule")
    schedule.active = False
    await emit_event(
        db,
        "schedule.deleted",
        actor_id=str(user["id"]),
        actor_role="consumer",
        resource_type="schedule",
        resource_id=str(schedule.id),
    )
    await db.commit()
