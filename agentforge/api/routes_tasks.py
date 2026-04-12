"""Task routes: submit and track agent task contracts."""

import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
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


async def _check_task_access(
    task: Task, user: dict, db: AsyncSession
) -> None:
    """Verify the user has access to this task."""
    if user["role"] == "consumer" and task.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your task")
    if user["role"] == "provider":
        agent_result = await db.execute(select(Agent).where(Agent.id == task.agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent or agent.provider_id != user["id"]:
            raise HTTPException(status_code=403, detail="Not your agent's task")


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

    # Budget enforcement: reject if agent base price exceeds consumer's max_cost_usd
    agent_price = agent.card.get("pricing", {}).get("base_price_usd", 0)
    budget_cap = req.constraints.max_cost_usd
    if budget_cap is not None and agent_price > budget_cap:
        raise HTTPException(
            status_code=400,
            detail=f"Agent price ${agent_price:.2f} exceeds budget ${budget_cap:.2f}",
        )

    # Timeout enforcement: cap at agent's max, floor at 60s
    caps = agent.card.get("capabilities", {}).get("constraints", {})
    agent_timeout_max = caps.get("timeout_max", 3600)
    task_timeout = req.constraints.timeout
    if task_timeout is not None:
        task_timeout = max(60, min(task_timeout, agent_timeout_max))
    else:
        task_timeout = agent_timeout_max

    constraints_dict = {
        "timeout": task_timeout,
        "max_cost_usd": req.constraints.max_cost_usd,
    }

    task = Task(
        id=_generate_task_id(),
        consumer_id=user["id"],
        agent_id=req.agent_id,
        inputs=req.inputs,
        constraints=constraints_dict,
        callback_url=req.callback_url,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

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

    await _check_task_access(task, user, db)
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

    await _check_task_access(task, user, db)

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
            results_path=e.results_path,
            created_at=e.created_at,
        )
        for e in executions
    ]


_ALLOWED_RESULT_FILES = {"output.md", "stdout.log", "stderr.log", "usage.json"}


@router.get("/{task_id}/result")
async def get_task_result(
    task_id: str,
    file: str = "output.md",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a result file from a completed task execution."""
    if file not in _ALLOWED_RESULT_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"File must be one of: {', '.join(sorted(_ALLOWED_RESULT_FILES))}",
        )

    # Auth: verify task ownership
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await _check_task_access(task, user, db)

    # Get latest execution with results
    result = await db.execute(
        select(Execution)
        .where(Execution.task_id == task_id)
        .where(Execution.results_path.isnot(None))
        .order_by(Execution.created_at.desc())
        .limit(1)
    )
    execution = result.scalar_one_or_none()
    if not execution or not execution.results_path:
        raise HTTPException(status_code=404, detail="No results available")

    file_path = Path(execution.results_path) / file
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{file}' not found")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    media = "application/json" if file.endswith(".json") else "text/plain"
    return PlainTextResponse(content=content, media_type=media)
