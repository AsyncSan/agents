"""Dashboard routes: usage analytics, cost tracking, and compliance export."""

import csv
import io
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.api.schemas import (
    AgentUsageSummary,
    ComplianceExportRequest,
    DailyUsage,
    DashboardResponse,
)
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.event_log import EventLog
from agentforge.models.execution import Execution
from agentforge.models.task import Task

router = APIRouter(prefix="/v1/me", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Usage dashboard with cost tracking, execution trends, and top agents."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    if user["role"] == "consumer":
        task_filter = Task.consumer_id == user["id"]
    else:
        # Provider sees stats for their agents
        task_filter = Task.agent_id.in_(
            select(Agent.id).where(Agent.provider_id == user["id"])
        )

    # Total aggregates
    totals = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(Task.id).filter(Task.status == "completed").label("success"),
            func.count(Task.id).filter(Task.status == "failed").label("failed"),
            func.coalesce(func.sum(Task.amount_captured_cents), 0).label("cost"),
        )
        .where(task_filter, Task.created_at >= start)
    )
    row = totals.one()
    total_execs = row[0] or 0
    total_success = row[1] or 0
    total_failed = row[2] or 0
    total_cost = row[3] or 0
    avg_cost = round(total_cost / total_execs, 2) if total_execs > 0 else None

    # Daily breakdown
    daily_query = (
        select(
            cast(Task.created_at, Date).label("day"),
            func.count(Task.id).label("total"),
            func.count(Task.id).filter(Task.status == "completed").label("success"),
            func.count(Task.id).filter(Task.status == "failed").label("failed"),
            func.coalesce(func.sum(Task.amount_captured_cents), 0).label("cost"),
            func.coalesce(
                func.sum(
                    select(func.coalesce(func.sum(Execution.elapsed_seconds), 0))
                    .where(Execution.task_id == Task.id)
                    .correlate(Task)
                    .scalar_subquery()
                ),
                0,
            ).label("duration"),
        )
        .where(task_filter, Task.created_at >= start)
        .group_by(cast(Task.created_at, Date))
        .order_by(cast(Task.created_at, Date))
    )
    daily_result = await db.execute(daily_query)
    daily_usage = [
        DailyUsage(
            date=str(r[0]),
            executions=r[1],
            success=r[2],
            failed=r[3],
            total_cost_cents=r[4],
            total_duration_seconds=r[5],
        )
        for r in daily_result.all()
    ]

    # Top agents by execution count
    top_query = (
        select(
            Task.agent_id,
            func.count(Task.id).label("execs"),
            func.coalesce(func.sum(Task.amount_captured_cents), 0).label("cost"),
        )
        .where(task_filter, Task.created_at >= start)
        .group_by(Task.agent_id)
        .order_by(func.count(Task.id).desc())
        .limit(10)
    )
    top_result = await db.execute(top_query)
    top_agents = []
    for r in top_result.all():
        # Get agent name
        agent_result = await db.execute(select(Agent.name).where(Agent.id == r[0]))
        agent_name = agent_result.scalar() or r[0]

        # Avg duration for this agent
        dur_result = await db.execute(
            select(func.avg(Execution.elapsed_seconds))
            .join(Task, Task.id == Execution.task_id)
            .where(task_filter, Task.agent_id == r[0], Task.created_at >= start)
        )
        avg_dur = dur_result.scalar()

        top_agents.append(
            AgentUsageSummary(
                agent_id=r[0],
                agent_name=agent_name,
                executions=r[1],
                total_cost_cents=r[2],
                avg_duration_seconds=round(float(avg_dur), 1) if avg_dur else None,
            )
        )

    return DashboardResponse(
        period_days=days,
        total_executions=total_execs,
        total_success=total_success,
        total_failed=total_failed,
        total_cost_cents=total_cost,
        avg_cost_per_run_cents=avg_cost,
        daily_usage=daily_usage,
        top_agents=top_agents,
    )


@router.post("/compliance/export")
async def export_compliance(
    req: ComplianceExportRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export audit log for compliance (SOC 2, ISO 27001).

    Returns all events for the authenticated user within the date range.
    """
    try:
        start = datetime.fromisoformat(req.start_date).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(req.end_date).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    except ValueError:
        raise APIError(422, ErrorCode.INVALID_DATE, "Invalid date format. Use YYYY-MM-DD")

    if (end - start).days > 365:
        raise APIError(400, ErrorCode.DATE_RANGE_TOO_LARGE, "Maximum range is 365 days")

    result = await db.execute(
        select(EventLog)
        .where(
            EventLog.actor_id == str(user["id"]),
            EventLog.created_at >= start,
            EventLog.created_at <= end,
        )
        .order_by(EventLog.created_at.asc())
    )
    events = result.scalars().all()

    if req.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "event_id", "timestamp", "event_type", "actor_id", "actor_role",
            "resource_type", "resource_id", "payload",
        ])
        for e in events:
            writer.writerow([
                str(e.id),
                e.created_at.isoformat(),
                e.event_type,
                e.actor_id,
                e.actor_role,
                e.resource_type,
                e.resource_id,
                json.dumps(e.payload) if e.payload else "",
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=audit-log-{req.start_date}-{req.end_date}.csv"
                )
            },
        )

    # JSON format
    entries = [
        {
            "event_id": str(e.id),
            "timestamp": (
                e.created_at.isoformat()
            ),
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "actor_role": e.actor_role,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "payload": e.payload,
        }
        for e in events
    ]
    export = {
        "export_type": "compliance_audit_log",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": req.start_date, "end": req.end_date},
        "total_events": len(entries),
        "events": entries,
    }
    return Response(
        content=json.dumps(export, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f"attachment; filename=audit-log-{req.start_date}-{req.end_date}.json"
            )
        },
    )
