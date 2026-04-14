"""Task routes: submit and track agent task contracts."""

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user, require_role
from agentforge.api.errors import APIError, ErrorCode
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
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your task")
    if user["role"] == "provider":
        agent_result = await db.execute(select(Agent).where(Agent.id == task.agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent or agent.provider_id != user["id"]:
            raise APIError(403, ErrorCode.FORBIDDEN, "Not your agent's task")


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
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, "Agent not found or inactive")

    # Budget enforcement: reject if agent base price exceeds consumer's max_cost_usd
    agent_price = agent.card.get("pricing", {}).get("base_price_usd", 0)
    budget_cap = req.constraints.max_cost_usd
    if budget_cap is not None and agent_price > budget_cap:
        raise APIError(
            400, ErrorCode.BUDGET_EXCEEDED,
            f"Agent price ${agent_price:.2f} exceeds budget ${budget_cap:.2f}",
            {"agent_price_usd": agent_price, "budget_cap_usd": budget_cap},
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
        compute_tier=req.compute_tier,
        payment_rail=req.payment_rail,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return _task_to_response(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    agent_id: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks for the current user. Supports filtering by status, agent, and date range."""
    if user["role"] == "consumer":
        query = select(Task).where(Task.consumer_id == user["id"])
    else:
        query = (
            select(Task)
            .join(Agent, Task.agent_id == Agent.id)
            .where(Agent.provider_id == user["id"])
        )

    if status:
        query = query.where(Task.status == status)
    if agent_id:
        query = query.where(Task.agent_id == agent_id)
    if created_after:
        query = query.where(Task.created_at >= created_after)
    if created_before:
        query = query.where(Task.created_at <= created_before)

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
        raise APIError(404, ErrorCode.TASK_NOT_FOUND, "Task not found")

    await _check_task_access(task, user, db)
    return _task_to_response(task)


@router.get("/{task_id}/executions", response_model=list[ExecutionResponse])
async def get_task_executions(
    task_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all executions for a task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise APIError(404, ErrorCode.TASK_NOT_FOUND, "Task not found")

    await _check_task_access(task, user, db)

    result = await db.execute(
        select(Execution)
        .where(Execution.task_id == task_id)
        .order_by(Execution.created_at.desc())
        .offset(offset)
        .limit(limit)
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
        raise APIError(
            400, ErrorCode.INVALID_INPUT,
            f"File must be one of: {', '.join(sorted(_ALLOWED_RESULT_FILES))}",
        )

    # Auth: verify task ownership
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise APIError(404, ErrorCode.TASK_NOT_FOUND, "Task not found")
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
        raise APIError(404, ErrorCode.RESULT_NOT_FOUND, "No results available")

    file_path = Path(execution.results_path) / file
    if not file_path.is_file():
        raise APIError(404, ErrorCode.FILE_NOT_FOUND, f"File '{file}' not found")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    media = "application/json" if file.endswith(".json") else "text/plain"
    return PlainTextResponse(content=content, media_type=media)


log = logging.getLogger("agentforge.tasks")

_CANCELLABLE_STATUSES = {"pending", "running"}


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running task.

    Pending tasks are cancelled immediately. Running tasks trigger
    server destruction to stop execution.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise APIError(404, ErrorCode.TASK_NOT_FOUND, "Task not found")

    if task.consumer_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your task")

    if task.status not in _CANCELLABLE_STATUSES:
        raise APIError(
            409, ErrorCode.TASK_NOT_CANCELLABLE,
            f"Task status '{task.status}' cannot be cancelled",
            {"current_status": task.status, "cancellable": list(_CANCELLABLE_STATUSES)},
        )

    was_running = task.status == "running"
    task.status = "cancelled"
    await db.commit()

    # If running, destroy the server in background
    if was_running:
        exec_result = await db.execute(
            select(Execution)
            .where(Execution.task_id == task_id, Execution.status == "running")
            .order_by(Execution.created_at.desc())
            .limit(1)
        )
        execution = exec_result.scalar_one_or_none()
        if execution and execution.server_id:
            execution.status = "cancelled"
            await db.commit()
            asyncio.create_task(_destroy_server_async(execution.server_id))

    await db.refresh(task)
    return _task_to_response(task)


async def _destroy_server_async(server_id: str) -> None:
    """Destroy a Hetzner server in the background."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "hcloud", "server", "delete", server_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            log.info(f"Cancelled task: destroyed server {server_id}")
        else:
            log.warning(f"Failed to destroy server {server_id}: {stderr.decode()}")
    except Exception as e:
        log.error(f"Error destroying server {server_id}: {e}")
