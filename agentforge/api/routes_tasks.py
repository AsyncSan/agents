"""Task routes: submit and track agent task contracts."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user, require_role
from agentforge.api.schemas import (
    ExecutionResponse,
    TaskCreateRequest,
    TaskListResponse,
    TaskResponse,
)
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.execution import Execution
from agentforge.models.task import Task

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


def _generate_task_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"tc-{now}-{suffix}"


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        agent_id=task.agent_id,
        consumer_id=task.consumer_id,
        status=task.status,
        inputs=task.inputs,
        constraints=task.constraints,
        callback_url=task.callback_url,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    req: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new task contract for an agent."""
    # Verify agent exists and is active
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if not agent or agent.status != "active":
        raise HTTPException(status_code=404, detail="Agent not found or inactive")

    task = Task(
        id=_generate_task_id(),
        consumer_id=user["id"],
        agent_id=req.agent_id,
        inputs=req.inputs,
        constraints=req.constraints,
        callback_url=req.callback_url,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # TODO: Phase 2, trigger dispatch in background
    # background_tasks.add_task(dispatch_task, task.id)

    return _task_to_response(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks for the current user."""
    if user["role"] == "consumer":
        query = select(Task).where(Task.consumer_id == user["id"])
    else:
        # Providers see tasks for their agents
        query = (
            select(Task)
            .join(Agent, Task.agent_id == Agent.id)
            .where(Agent.provider_id == user["id"])
        )

    if status:
        query = query.where(Task.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(tasks=[_task_to_response(t) for t in tasks], total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task details."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Authorization check
    if user["role"] == "consumer" and task.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your task")

    return _task_to_response(task)


@router.get("/{task_id}/executions", response_model=list[ExecutionResponse])
async def get_task_executions(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all executions for a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await db.execute(
        select(Execution).where(Execution.task_id == task_id).order_by(Execution.created_at.desc())
    )
    executions = result.scalars().all()

    return [
        ExecutionResponse(
            id=e.id,
            task_id=e.task_id,
            server_id=e.server_id,
            status=e.status,
            started_at=e.started_at,
            completed_at=e.completed_at,
            elapsed_seconds=e.elapsed_seconds,
            exit_code=e.exit_code,
            metrics=e.metrics,
            created_at=e.created_at,
        )
        for e in executions
    ]
