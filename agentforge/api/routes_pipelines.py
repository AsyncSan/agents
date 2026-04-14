"""Pipeline routes: create and track agent composition chains."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user, require_role
from agentforge.api.errors import APIError, ErrorCode
from agentforge.api.schemas import (
    PipelineCreateRequest,
    PipelineListResponse,
    PipelineResponse,
    TaskResponse,
)
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.pipeline import Pipeline
from agentforge.models.task import Task

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])


def _generate_pipeline_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"pl-{now}-{suffix}"


def _generate_task_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"tc-{now}-{suffix}"


def _pipeline_to_response(pipeline: Pipeline) -> PipelineResponse:
    tasks = [
        TaskResponse(
            id=t.id,
            agent_id=t.agent_id,
            consumer_id=t.consumer_id,
            status=t.status,
            inputs=t.inputs,
            constraints=t.constraints,
            callback_url=t.callback_url,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in (pipeline.tasks or [])
    ]
    return PipelineResponse(
        id=pipeline.id,
        consumer_id=pipeline.consumer_id,
        status=pipeline.status,
        current_step=pipeline.current_step,
        total_steps=pipeline.total_steps or len(pipeline.steps),
        chain_trust_score=float(pipeline.chain_trust_score)
        if pipeline.chain_trust_score is not None
        else None,
        steps=pipeline.steps,
        tasks=tasks,
        context=pipeline.context,
        total_authorized_cents=pipeline.total_authorized_cents,
        total_captured_cents=pipeline.total_captured_cents,
        max_cost_usd=float(pipeline.max_cost_usd)
        if pipeline.max_cost_usd is not None
        else None,
        callback_url=pipeline.callback_url,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
    )


def _normalize_step_indices(steps: list) -> list:
    """Assign step_index to steps that don't have one.

    Steps without explicit step_index get sequential indices.
    Steps sharing the same step_index run in parallel.
    """
    normalized = []
    auto_index = 0
    has_explicit = any(s.step_index is not None for s in steps)

    if not has_explicit:
        # All sequential (backward compatible)
        for i, step in enumerate(steps):
            normalized.append((i, step))
        return normalized

    # With explicit indices: assign auto-incrementing to unset ones
    prev_explicit = -1
    for step in steps:
        if step.step_index is not None:
            auto_index = step.step_index
            prev_explicit = auto_index
        else:
            # Auto-increment from last seen index
            if prev_explicit >= 0:
                auto_index = prev_explicit + 1
                prev_explicit = auto_index
            # else stays at 0
        normalized.append((auto_index, step))
        if step.step_index is None:
            auto_index += 1
            prev_explicit = auto_index - 1

    return normalized


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    req: PipelineCreateRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Create a pipeline of agent tasks. Steps sharing step_index run in parallel."""
    # Normalize step indices
    indexed_steps = _normalize_step_indices(req.steps)

    # Validate all agents exist and are active
    agent_ids = [step.agent_id for _, step in indexed_steps]
    result = await db.execute(select(Agent).where(Agent.id.in_(agent_ids)))
    agents = {a.id: a for a in result.scalars().all()}

    for _, step in indexed_steps:
        if step.agent_id not in agents:
            raise APIError(
                404, ErrorCode.AGENT_NOT_FOUND,
                f"Agent '{step.agent_id}' not found",
            )
        if agents[step.agent_id].status != "active":
            raise APIError(
                400, ErrorCode.INVALID_INPUT,
                f"Agent '{step.agent_id}' is not active",
            )

    # Budget enforcement: sum of all agent base prices
    total_price = sum(
        agents[s.agent_id].card.get("pricing", {}).get("base_price_usd", 0)
        for _, s in indexed_steps
    )
    budget_cap = req.constraints.max_cost_usd
    if budget_cap is not None and total_price > budget_cap:
        raise APIError(
            400, ErrorCode.BUDGET_EXCEEDED,
            f"Pipeline total ${total_price:.2f} exceeds budget ${budget_cap:.2f}",
            {"total_price_usd": total_price, "budget_cap_usd": budget_cap},
        )

    # Chain trust = min of all agent trust scores
    trust_scores = [
        float(agents[s.agent_id].trust_score or 0) for _, s in indexed_steps
    ]
    chain_trust = min(trust_scores) if trust_scores else 0.0

    # Serialize steps with step_index and optional condition
    steps_data = [
        {
            "agent_id": step.agent_id,
            "inputs": step.inputs,
            "output_map": step.output_map,
            "constraints": step.constraints.model_dump(),
            "step_index": idx,
            **(
                {"condition": step.condition.model_dump()}
                if step.condition
                else {}
            ),
        }
        for idx, step in indexed_steps
    ]

    # Count distinct step groups
    max_step = max(idx for idx, _ in indexed_steps)

    pipeline = Pipeline(
        id=_generate_pipeline_id(),
        consumer_id=user["id"],
        status="pending",
        callback_url=req.callback_url,
        max_cost_usd=req.constraints.max_cost_usd,
        steps=steps_data,
        current_step=0,
        chain_trust_score=chain_trust,
        total_steps=max_step + 1,
    )
    db.add(pipeline)

    # Create tasks for step_index=0 (could be multiple if parallel)
    for idx, step in indexed_steps:
        if idx != 0:
            continue
        task = Task(
            id=_generate_task_id(),
            consumer_id=user["id"],
            agent_id=step.agent_id,
            inputs=step.inputs,
            constraints=step.constraints.model_dump(),
            pipeline_id=pipeline.id,
            step_index=0,
            status="pending",
        )
        db.add(task)

    await db.commit()
    await db.refresh(pipeline)

    return _pipeline_to_response(pipeline)


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pipeline status with all task statuses."""
    result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise APIError(404, ErrorCode.PIPELINE_NOT_FOUND, "Pipeline not found")
    if user["role"] == "consumer" and pipeline.consumer_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your pipeline")

    return _pipeline_to_response(pipeline)


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    status: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """List pipelines for the current consumer."""
    query = select(Pipeline).where(Pipeline.consumer_id == user["id"])
    if status:
        query = query.where(Pipeline.status == status)
    if created_after:
        query = query.where(Pipeline.created_at >= created_after)
    if created_before:
        query = query.where(Pipeline.created_at <= created_before)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Pipeline.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    pipelines = result.scalars().all()

    return PipelineListResponse(
        pipelines=[_pipeline_to_response(p) for p in pipelines],
        total=total,
    )


# --- Pipeline Shared Context ---


@router.get("/{pipeline_id}/context")
async def get_pipeline_context(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read the shared pipeline context."""
    result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise APIError(404, ErrorCode.PIPELINE_NOT_FOUND, "Pipeline not found")
    if user["role"] == "consumer" and pipeline.consumer_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your pipeline")

    return pipeline.context or {}


@router.put("/{pipeline_id}/context")
async def update_pipeline_context(
    pipeline_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge keys into the shared pipeline context.

    Used by agents/workers to share structured data between steps.
    Keys are merged (not replaced). Set a key to null to delete it.
    """
    result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise APIError(404, ErrorCode.PIPELINE_NOT_FOUND, "Pipeline not found")

    # Merge context
    ctx = dict(pipeline.context or {})
    for key, value in body.items():
        if value is None:
            ctx.pop(key, None)
        else:
            ctx[key] = value
    pipeline.context = ctx
    await db.commit()

    return ctx
